from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

APP_TITLE = "HuevoHelper"
DEFAULT_URL = "https://huevo.su/clicker"
MAX_CLICKS_PER_SESSION = 10000
MAX_CPS = 5
SCAN_SCRIPT = r"""
() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
      s.visibility !== 'hidden' && s.display !== 'none';
  };
  const textOf = (el) => (el.innerText || el.getAttribute('aria-label') ||
    el.getAttribute('title') || el.getAttribute('alt') ||
    el.getAttribute('placeholder') || el.value || '').trim()
    .replace(/\s+/g, ' ').slice(0, 100);
  const items = [...document.querySelectorAll('button, a[href], input, textarea, select, [role="button"]')]
    .filter(visible).slice(0, 300);
  return items.map((el, i) => {
    const tag = el.tagName.toLowerCase();
    const label = textOf(el) || '(без подписи)';
    const type = el.getAttribute('type') || '';
    let selector = '';
    if (el.id) selector = '#' + CSS.escape(el.id);
    else if (el.getAttribute('data-testid'))
      selector = '[data-testid="' + CSS.escape(el.getAttribute('data-testid')) + '"]';
    else {
      const same = [...document.querySelectorAll(tag)];
      selector = tag + ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
    }
    return {index:i, tag, type, label, selector, disabled: !!el.disabled};
  });
}
"""


class HuevoHelper:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1040x760")
        self.root.minsize(780, 560)
        self.items: list[dict] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.running = False
        self.click_count = 0
        self.session_clicks = 0
        self.started_at: float | None = None
        self.interval_ms = 200
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._log("Готово. Авторизуйтесь вручную в открывшемся браузере.")

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="HuevoHelper", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Откройте clicker, войдите вручную, выберите элемент копилки и нажмите «Старт».",
        ).pack(anchor="w", pady=(2, 10))

        address = ttk.Frame(outer)
        address.pack(fill="x", pady=(0, 8))
        ttk.Label(address, text="Страница:").pack(side="left")
        self.url_var = tk.StringVar(value=DEFAULT_URL)
        self.url_entry = ttk.Entry(address, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.open_btn = ttk.Button(address, text="Открыть браузер", command=self.open_browser)
        self.open_btn.pack(side="left")
        self.goto_btn = ttk.Button(address, text="Перейти к clicker", command=self.go_to_clicker, state="disabled")
        self.goto_btn.pack(side="left", padx=(6, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))
        self.scan_btn = ttk.Button(controls, text="Обновить элементы", command=self.scan, state="disabled")
        self.scan_btn.pack(side="left")
        self.click_btn = ttk.Button(controls, text="Один клик", command=self.click_selected, state="disabled")
        self.click_btn.pack(side="left", padx=6)
        self.start_btn = ttk.Button(controls, text="▶ Старт автокликера", command=self.start_clicker, state="disabled")
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(controls, text="■ Стоп", command=self.stop_clicker, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.status_var = tk.StringVar(value="Браузер не открыт")
        ttk.Label(controls, textvariable=self.status_var).pack(side="right")

        stats = ttk.LabelFrame(outer, text="Статистика сессии", padding=8)
        stats.pack(fill="x", pady=(0, 8))
        self.total_var = tk.StringVar(value="0")
        self.session_var = tk.StringVar(value="0")
        self.rate_var = tk.StringVar(value="0.0 клика/с")
        self.elapsed_var = tk.StringVar(value="00:00:00")
        for col, (label, variable) in enumerate([
            ("Всего успешных кликов", self.total_var),
            ("В этой сессии", self.session_var),
            ("Средняя скорость", self.rate_var),
            ("Время работы", self.elapsed_var),
        ]):
            cell = ttk.Frame(stats, padding=(6, 2))
            cell.grid(row=0, column=col, sticky="ew")
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Label(cell, textvariable=variable, font=("Segoe UI", 13, "bold")).pack(anchor="w")
            stats.columnconfigure(col, weight=1)

        columns = ("tag", "label", "type", "selector", "state")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse", height=10)
        for col, title, width in [
            ("tag", "Тип", 70), ("label", "Текст / подпись", 260),
            ("type", "HTML type", 90), ("selector", "Селектор", 300), ("state", "Состояние", 90)
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, minwidth=50, stretch=(col in ("label", "selector")))
        yscroll = ttk.Scrollbar(outer, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(outer, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(fill="both", expand=True, side="top")
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x")

        log_frame = ttk.LabelFrame(outer, text="Логи", padding=6)
        log_frame.pack(fill="both", expand=False, pady=(8, 0))
        self.log_text = tk.Text(log_frame, height=6, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Label(
            outer,
            text=f"Лимит защиты: до {MAX_CPS} кликов/с и {MAX_CLICKS_PER_SESSION:,} кликов за сессию. "
                 "Пароли не считываются и не сохраняются. Не используйте автоматизацию в обход правил сайта.",
            wraplength=980,
        ).pack(anchor="w", pady=(8, 0))

    def _log(self, message: str):
        if not hasattr(self, "log_text"):
            return
        stamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{stamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def open_browser(self):
        if self.browser:
            try:
                if self.page and not self.page.is_closed():
                    self.page.bring_to_front()
                    return
            except Exception:
                pass
        url = self.url_var.get().strip()
        parsed = urlparse(url if "://" in url else "https://" + url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            messagebox.showerror("Некорректный адрес", "Введите корректный адрес сайта.")
            return
        url = parsed.geturl()
        self.url_var.set(url)
        self.open_btn.configure(state="disabled")
        self.status_var.set("Запуск браузера…")
        self.root.update_idletasks()
        try:
            # Keep all synchronous Playwright operations on the Tk main thread.
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self.scan_btn.configure(state="normal")
            self.goto_btn.configure(state="normal")
            self.status_var.set("Браузер открыт")
            self._log(f"Открыта страница: {url}")
            self.scan()
        except Exception as exc:
            self._log(f"Ошибка запуска браузера: {exc}")
            self.status_var.set("Ошибка запуска браузера")
            messagebox.showerror(
                "Не удалось открыть браузер",
                "Проверьте установку Chromium командой:\npy -m playwright install chromium\n\n"
                + str(exc)[:1400],
            )
            self._dispose_browser()
            self.open_btn.configure(state="normal")

    def go_to_clicker(self):
        if not self.page:
            return
        try:
            self.page.goto(DEFAULT_URL, wait_until="domcontentloaded", timeout=60000)
            self.url_var.set(DEFAULT_URL)
            self._log(f"Переход: {DEFAULT_URL}")
            self.scan()
        except Exception as exc:
            self._log(f"Не удалось перейти на clicker: {exc}")
            messagebox.showerror("Ошибка перехода", str(exc)[:1200])

    def scan(self):
        if not self.page:
            return
        try:
            self.items = self.page.evaluate(SCAN_SCRIPT)
            for row in self.tree.get_children():
                self.tree.delete(row)
            for i, item in enumerate(self.items):
                state = "отключён" if item["disabled"] else "доступен"
                self.tree.insert(
                    "", "end", iid=str(i),
                    values=(item["tag"], item["label"], item["type"], item["selector"], state),
                )
            self.status_var.set(f"Найдено элементов: {len(self.items)}")
            self.click_btn.configure(state="normal" if self.items else "disabled")
            self.start_btn.configure(state="normal" if self.items and not self.running else "disabled")
            self._log(f"Обновлён список: {len(self.items)} элементов")
        except Exception as exc:
            self._log(f"Ошибка чтения страницы: {exc}")
            messagebox.showerror("Не удалось прочитать страницу", str(exc)[:1200])

    def _selected_item(self):
        selection = self.tree.selection()
        if not selection or not self.page:
            messagebox.showinfo("Выберите элемент", "Сначала выберите строку в списке элементов.")
            return None
        item = self.items[int(selection[0])]
        if item["disabled"]:
            messagebox.showwarning("Элемент отключён", "Выбранный элемент отключён.")
            return None
        return item

    def click_selected(self):
        item = self._selected_item()
        if item is None:
            return
        try:
            self.page.locator(item["selector"]).first.click(timeout=5000)
            self.click_count += 1
            self.session_clicks += 1
            self._refresh_stats()
            self.status_var.set("Один клик выполнен")
            self._log(f"Клик выполнен: {item['label']} | всего: {self.click_count}")
            self.root.after(300, self.scan)
        except PlaywrightTimeoutError:
            self._log(f"Тайм-аут клика по элементу: {item['label']}")
            messagebox.showerror("Не удалось нажать", "Элемент не найден или не реагирует на клик.")
        except Exception as exc:
            self._log(f"Ошибка клика: {exc}")
            messagebox.showerror("Ошибка клика", str(exc)[:1200])

    def start_clicker(self):
        if self.running:
            return
        item = self._selected_item()
        if item is None:
            return
        if self.session_clicks >= MAX_CLICKS_PER_SESSION:
            messagebox.showwarning("Достигнут лимит", "Достигнут лимит кликов этой сессии.")
            return
        confirm = messagebox.askyesno(
            "Запустить автокликер?",
            f"Автокликер будет нажимать выбранный элемент до остановки.\n\n"
            f"Элемент: {item['label']}\nСкорость: до {MAX_CPS} кликов/с\n"
            f"Лимит сессии: {MAX_CLICKS_PER_SESSION:,} кликов.\n\n"
            "Продолжайте только если автоматизация разрешена правилами сайта.",
        )
        if not confirm:
            return
        self.running = True
        self.active_item = item
        self.started_at = time.monotonic()
        self.session_clicks = 0
        self.interval_ms = round(1000 / MAX_CPS)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.scan_btn.configure(state="disabled")
        self.click_btn.configure(state="disabled")
        self.status_var.set("Автокликер работает")
        self._log(f"Старт: {item['label']} | ограничение {MAX_CPS} кликов/с")
        self._click_tick()

    def _click_tick(self):
        if not self.running:
            return
        if self.session_clicks >= MAX_CLICKS_PER_SESSION:
            self.stop_clicker(reason="Достигнут лимит кликов сессии.")
            return
        try:
            item = self.active_item
            locator = self.page.locator(item["selector"]).first
            locator.click(timeout=1500)
            self.click_count += 1
            self.session_clicks += 1
            if self.session_clicks == 1 or self.session_clicks % 10 == 0:
                self._log(f"Успешных кликов в сессии: {self.session_clicks} | всего: {self.click_count}")
            self._refresh_stats()
            self.root.after(self.interval_ms, self._click_tick)
        except Exception as exc:
            self._log(f"Автокликер остановлен: {exc}")
            self.stop_clicker(reason="Элемент исчез или клик завершился ошибкой.")
            messagebox.showwarning("Автокликер остановлен", "Не удалось нажать элемент. Обновите список и выберите его снова.")

    def stop_clicker(self, reason: str = "Остановлено пользователем."):
        was_running = self.running
        self.running = False
        self.stop_btn.configure(state="disabled")
        self.start_btn.configure(state="normal" if self.items else "disabled")
        self.scan_btn.configure(state="normal" if self.page else "disabled")
        self.click_btn.configure(state="normal" if self.items else "disabled")
        self.status_var.set("Автокликер остановлен")
        if was_running:
            self._log(f"{reason} Клики в сессии: {self.session_clicks}")
        self._refresh_stats()

    def _refresh_stats(self):
        self.total_var.set(f"{self.click_count:,}")
        self.session_var.set(f"{self.session_clicks:,}")
        elapsed = max(0.0, time.monotonic() - self.started_at) if self.started_at else 0.0
        self.elapsed_var.set(time.strftime("%H:%M:%S", time.gmtime(elapsed)))
        rate = self.session_clicks / elapsed if elapsed > 0 else 0.0
        self.rate_var.set(f"{rate:.1f} клика/с")

    def _dispose_browser(self):
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.context = self.browser = self.playwright = self.page = None

    def close(self):
        self.stop_clicker(reason="Приложение закрывается.")
        self._dispose_browser()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    app = HuevoHelper(root)
    root.mainloop()
