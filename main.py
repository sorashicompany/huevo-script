from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


APP_TITLE = "Huevo Desktop Helper"
DEFAULT_URL = "https://example.com"
SCAN_SCRIPT = r"""
() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 &&
      s.visibility !== 'hidden' && s.display !== 'none';
  };
  const textOf = (el) => (el.innerText || el.getAttribute('aria-label') ||
    el.getAttribute('placeholder') || el.value || el.title || '').trim()
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
        self.root.geometry("900x620")
        self.root.minsize(720, 480)
        self.items: list[dict] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.browser_thread: threading.Thread | None = None
        self.messages: queue.Queue | None = None
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Huevo Desktop Helper", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Откройте сайт, обновите список элементов и выберите действие вручную.",
        ).pack(anchor="w", pady=(2, 10))

        address = ttk.Frame(outer)
        address.pack(fill="x", pady=(0, 8))
        ttk.Label(address, text="Адрес сайта:").pack(side="left")
        self.url_var = tk.StringVar(value=DEFAULT_URL)
        self.url_entry = ttk.Entry(address, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.open_btn = ttk.Button(address, text="Открыть браузер", command=self.open_browser)
        self.open_btn.pack(side="left")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))
        self.scan_btn = ttk.Button(controls, text="Обновить элементы", command=self.scan, state="disabled")
        self.scan_btn.pack(side="left")
        self.click_btn = ttk.Button(controls, text="Нажать выбранный элемент…", command=self.click_selected, state="disabled")
        self.click_btn.pack(side="left", padx=8)
        self.status_var = tk.StringVar(value="Браузер не открыт")
        ttk.Label(controls, textvariable=self.status_var).pack(side="right")

        columns = ("tag", "label", "type", "selector", "state")
        self.tree = ttk.Treeview(outer, columns=columns, show="headings", selectmode="browse")
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
        yscroll.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, anchor="ne")
        xscroll.pack(fill="x")

        ttk.Label(
            outer,
            text="Подсказка: авторизация выполняется вручную в окне браузера. Приложение не сохраняет пароли.",
            wraplength=850,
        ).pack(anchor="w", pady=(10, 0))

    def open_browser(self):
        url = self.url_var.get().strip()
        parsed = urlparse(url if "://" in url else "https://" + url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            messagebox.showerror("Некорректный адрес", "Введите корректный адрес сайта, например https://example.com")
            return
        url = parsed.geturl()
        self.url_var.set(url)
        self.open_btn.configure(state="disabled")
        self.status_var.set("Запуск браузера…")
        threading.Thread(target=self._start_browser, args=(url,), daemon=True).start()

    def _start_browser(self, url: str):
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self.root.after(0, lambda: self._browser_ready(pw, browser, context, page))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda m=msg: self._browser_error(m))

    def _browser_ready(self, pw, browser, context, page):
        self.playwright, self.browser, self.context, self.page = pw, browser, context, page
        self.open_btn.configure(state="normal")
        self.scan_btn.configure(state="normal")
        self.status_var.set("Браузер открыт")
        self.scan()

    def _browser_error(self, message: str):
        self.open_btn.configure(state="normal")
        self.status_var.set("Не удалось открыть браузер")
        if "Executable doesn't exist" in message or "playwright install" in message.lower():
            messagebox.showerror(
                "Не установлен Chromium",
                "Установите браузер командой:\n\npy -m playwright install chromium\n\n"
                "Затем перезапустите приложение.\n\nПодробности:\n" + message[:1200],
            )
        else:
            messagebox.showerror("Ошибка запуска браузера", message[:1800])

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
        except Exception as exc:
            messagebox.showerror("Не удалось прочитать страницу", str(exc)[:1500])

    def click_selected(self):
        selection = self.tree.selection()
        if not selection or not self.page:
            messagebox.showinfo("Выберите элемент", "Сначала выберите строку в списке.")
            return
        item = self.items[int(selection[0])]
        if item["disabled"]:
            messagebox.showwarning("Элемент отключён", "Этот элемент отмечен сайтом как отключённый.")
            return
        description = f'{item["tag"]} — {item["label"]}\nСелектор: {item["selector"]}'
        if not messagebox.askyesno(
            "Подтвердите действие",
            "Нажать этот элемент на открытом сайте?\n\n" + description,
        ):
            return
        try:
            locator = self.page.locator(item["selector"]).first
            locator.click(timeout=5000)
            self.status_var.set("Элемент нажат")
            self.root.after(500, self.scan)
        except PlaywrightTimeoutError:
            messagebox.showerror("Не удалось нажать", "Элемент не найден или не реагирует на нажатие.")
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc)[:1500])

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    import queue  # kept local; no background task queue is needed by the UI

    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    app = HuevoHelper(root)
    root.mainloop()
