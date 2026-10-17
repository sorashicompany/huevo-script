from __future__ import annotations

import os
import subprocess
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from playwright.sync_api import sync_playwright

APP_TITLE = "Huevo Casino — Шарик"
GAME_URL = "https://huevo.su/apps/1"
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HuevoHelper" / "casino-profile"
PUMP_LIMIT = 3


class CasinoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("560x390")
        root.minsize(500, 350)
        self.playwright = self.browser = self.context = self.page = self.chrome_process = None
        self.running = False
        self.after_id = None
        self.base_bet = 1.0
        self.pumps = 0
        self.loss_handled = False
        self.round_started = False
        self.next_action_at = 0.0
        self.total_rounds = 0
        self.losses = 0
        self.wins = 0

        outer = ttk.Frame(root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=APP_TITLE, font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Автоматизация игры «Шарик» на huevo.su").pack(anchor="w", pady=(3, 12))

        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Начальная ставка:").pack(side="left")
        self.bet_var = tk.StringVar(value="1.00")
        ttk.Entry(row, textvariable=self.bet_var, width=12).pack(side="left", padx=8)
        ttk.Label(row, text="Ставка увеличивается ×2 после БАХ!").pack(side="left")

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="Открыть игру", command=self.open_browser).pack(side="left")
        self.toggle_btn = ttk.Button(buttons, text="Старт", command=self.toggle, state="disabled")
        self.toggle_btn.pack(side="left", padx=8)

        self.status = tk.StringVar(value="Сначала открой игру")
        ttk.Label(outer, textvariable=self.status, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.stats = tk.StringVar(value="Раунды: 0  |  Победы: 0  |  БАХ!: 0")
        ttk.Label(outer, textvariable=self.stats).pack(anchor="w", pady=(0, 8))
        lf = ttk.LabelFrame(outer, text="Логи", padding=6)
        lf.pack(fill="both", expand=True)
        self.logs = tk.Text(lf, height=8, wrap="word", state="disabled")
        self.logs.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.logs.yview)
        sb.pack(side="right", fill="y")
        self.logs.configure(yscrollcommand=sb.set)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def log(self, msg: str):
        self.logs.configure(state="normal")
        self.logs.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.logs.see("end")
        self.logs.configure(state="disabled")

    def update_stats(self):
        self.stats.set(f"Раунды: {self.total_rounds}  |  Победы: {self.wins}  |  БАХ!: {self.losses}")

    def locate_chrome(self):
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        paths = [
            local / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        return next((p for p in paths if p.is_file()), None)

    def open_browser(self):
        if self.page:
            try:
                if not self.page.is_closed():
                    self.page.bring_to_front()
                    return
            except Exception:
                pass
        try:
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            port_file = PROFILE_DIR / "DevToolsActivePort"
            port_file.unlink(missing_ok=True)
            chrome = self.locate_chrome()
            if not chrome:
                raise FileNotFoundError("Google Chrome не найден. Установи Google Chrome.")
            self.chrome_process = subprocess.Popen(
                [str(chrome), "--remote-debugging-port=0", f"--user-data-dir={PROFILE_DIR}",
                 "--no-first-run", "--no-default-browser-check", GAME_URL],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not port_file.exists():
                if self.chrome_process.poll() is not None:
                    raise RuntimeError("Chrome завершился до запуска.")
                time.sleep(0.2)
            if not port_file.exists():
                raise TimeoutError("Chrome не открыл интерфейс управления за 20 секунд.")
            port = port_file.read_text(encoding="utf-8").splitlines()[0].strip()
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp("http://127.0.0.1:" + port)
            if not self.browser.contexts:
                raise RuntimeError("Вкладки Chrome недоступны.")
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            if self.page.url == "about:blank":
                self.page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
            self.toggle_btn.configure(state="normal")
            self.status.set("Игра открыта — проверь вход и выбери «Шарик»")
            self.log("Браузер открыт. Если потребуется, выбери игру «Шарик» вручную.")
        except Exception as exc:
            self.log("Ошибка запуска: " + str(exc))
            messagebox.showerror("Ошибка запуска Chrome", str(exc)[:600])
            self.dispose()

    def frames(self):
        if not self.page:
            return []
        return list(self.page.frames)

    def first_visible(self, selector: str):
        for frame in self.frames():
            try:
                loc = frame.locator(selector)
                for i in range(min(loc.count(), 5)):
                    item = loc.nth(i)
                    if item.is_visible():
                        return item
            except Exception:
                continue
        return None

    def text_visible(self, text: str) -> bool:
        for frame in self.frames():
            try:
                loc = frame.get_by_text(text, exact=True)
                for i in range(min(loc.count(), 5)):
                    if loc.nth(i).is_visible():
                        return True
            except Exception:
                continue
        return False

    def set_bet(self, amount: float) -> bool:
        # The enabled decimal input is the editable stake field; avoid the disabled display field.
        for frame in self.frames():
            try:
                fields = frame.locator('input[inputmode="decimal"]:not([disabled])')
                for i in range(fields.count()):
                    field = fields.nth(i)
                    if field.is_visible() and field.is_enabled():
                        field.fill(f"{amount:.2f}")
                        field.press("Enter")
                        field.evaluate("(el) => el.dispatchEvent(new Event('change', {bubbles:true}))")
                        return True
            except Exception:
                continue
        return False

    def find_button(self, label: str):
        for frame in self.frames():
            try:
                buttons = frame.locator("button")
                for i in range(buttons.count()):
                    btn = buttons.nth(i)
                    if not btn.is_visible() or not btn.is_enabled():
                        continue
                    try:
                        if label == "Накачать" and "Накачать" in btn.inner_text():
                            return btn
                        if label == "×2" and "×2" in btn.inner_text():
                            return btn
                        if label == "Надуть шарик" and "Надуть шарик" in btn.inner_text():
                            return btn
                    except Exception:
                        pass
            except Exception:
                continue
        return None

    def toggle(self):
        if not self.page:
            return
        if not self.running:
            try:
                amount = float(self.bet_var.get().replace(",", "."))
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Неверная ставка", "Введи начальную ставку больше нуля.")
                return
            self.base_bet = amount
            self.pumps = 0
            self.loss_handled = False
            self.round_started = False
            if not self.set_bet(self.base_bet):
                self.log("Не найдено редактируемое поле ставки. Выбери игру «Шарик» и проверь поле ставки.")
                self.status.set("Не найдено поле ставки")
                return
            self.running = True
            self.toggle_btn.configure(text="Стоп")
            self.status.set("Работаю — ожидание игры «Шарик»")
            self.log(f"Автоматизация запущена. Начальная ставка: {self.base_bet:.2f}")
            self.tick()
        else:
            self.stop("Остановлено пользователем")

    def stop(self, reason: str):
        self.running = False
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        self.toggle_btn.configure(text="Старт")
        self.status.set(reason)
        self.log(reason)

    def tick(self):
        if not self.running or not self.page:
            return
        try:
            if self.page.is_closed():
                self.stop("Вкладка закрыта")
                return

            now = time.monotonic()
            if now < self.next_action_at:
                self.after_id = self.root.after(200, self.tick)
                return

            # The game signals a loss with the exact visible text БАХ!.
            if self.text_visible("БАХ!"):
                if not self.loss_handled:
                    self.loss_handled = True
                    self.losses += 1
                    self.total_rounds += 1
                    self.update_stats()
                    double_btn = self.find_button("×2")
                    if double_btn:
                        double_btn.click(timeout=1500)
                        self.log("Обнаружен БАХ! Нажата кнопка ×2.")
                    else:
                        self.log("Обнаружен БАХ!, но кнопка ×2 не найдена — остановка для безопасности.")
                        self.stop("Не найдена кнопка ×2")
                        return
                    self.pumps = 0
                    self.round_started = False
                    self.next_action_at = now + 1.2
                self.after_id = self.root.after(250, self.tick)
                return

            if self.loss_handled:
                self.loss_handled = False
                self.next_action_at = now + 0.4

            # Start a fresh round explicitly; this action counts as the first pump.
            if not self.round_started:
                start_btn = self.find_button("Надуть шарик")
                if not start_btn:
                    self.status.set("Ожидаю кнопку «Надуть шарик» — выбери игру «Шарик»")
                    self.after_id = self.root.after(700, self.tick)
                    return
                start_btn.click(timeout=1500)
                self.round_started = True
                self.pumps = 1
                self.log("Нажата кнопка «Надуть шарик» — ход 1/4.")
                self.next_action_at = now + 0.8
                self.after_id = self.root.after(250, self.tick)
                return

            pump_btn = self.find_button("Накачать")
            if not pump_btn:
                self.status.set("Ожидаю кнопку «Накачать» в игре «Шарик»")
                self.after_id = self.root.after(700, self.tick)
                return

            # Starting the balloon counts as pump one, so only three more pumps are needed.
            if self.pumps >= PUMP_LIMIT + 1:
                self.wins += 1
                self.total_rounds += 1
                self.update_stats()
                if not self.set_bet(self.base_bet):
                    self.log("Четыре нажатия без БАХ!, но поле ставки не найдено. Проверь экран игры.")
                    self.stop("Не удалось вернуть начальную ставку")
                    return
                self.log(f"Раунд без БАХ! Ставка возвращена к {self.base_bet:.2f}.")
                self.pumps = 0
                self.round_started = False
                self.next_action_at = now + 1.0
                self.after_id = self.root.after(250, self.tick)
                return

            pump_btn.click(timeout=1500)
            self.pumps += 1
            self.status.set(f"Раунд: ход {self.pumps}/4")
            self.log(f"Накачать: ход {self.pumps}/4")
            self.next_action_at = now + 0.8
            self.after_id = self.root.after(250, self.tick)
        except Exception as exc:
            self.log("Ошибка игры: " + str(exc)[:250])
            self.after_id = self.root.after(800, self.tick)

    def dispose(self):
        self.running = False
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
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
        try:
            if self.chrome_process and self.chrome_process.poll() is None:
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.chrome_process.kill()
        except Exception:
            pass
        self.browser = self.context = self.playwright = self.page = self.chrome_process = None

    def close(self):
        self.dispose()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    CasinoApp(root)
    root.mainloop()
