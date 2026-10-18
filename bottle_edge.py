"""
HuevoBottle Edge — separate Windows GUI app.
Does not modify the existing Chrome version.
Requires Microsoft Edge installed on the PC.
"""
import threading
import tkinter as tk
from tkinter import scrolledtext
from pathlib import Path
import time
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

GAME_URL = "https://huevo.su/apps/3"

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

PROFILE_DIR = app_dir() / "edge-bottle-profile"

class HuevoBottleEdgeApp:
    def __init__(self, root):
        self.root = root
        root.title("HuevoBottle — Microsoft Edge")
        root.geometry("560x390")
        root.minsize(500, 340)
        self.worker = None
        self.stop_event = threading.Event()
        self.context = None

        tk.Label(root, text="HuevoBottle — Microsoft Edge",
                 font=("Segoe UI", 15, "bold")).pack(pady=(14, 4))
        tk.Label(root, text="Отдельная версия. Chrome-версия не изменяется.",
                 font=("Segoe UI", 9)).pack(pady=(0, 10))

        controls = tk.Frame(root)
        controls.pack(pady=4)
        self.start_button = tk.Button(controls, text="Запустить в Edge",
                                      width=18, command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = tk.Button(controls, text="Остановить", width=14,
                                     command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.log_box = scrolledtext.ScrolledText(root, height=12, wrap=tk.WORD,
                                                 state=tk.DISABLED)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def log(self, message):
        def write():
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, message + "\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)
        self.root.after(0, write)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        self.stop_event.clear()
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.worker = threading.Thread(target=self.run_bot, daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.log("Остановка запрошена…")
        self.stop_button.configure(state=tk.DISABLED)

    def click_button(self, frame, selector, label):
        try:
            button = frame.locator(selector).first
            if button.is_visible(timeout=1200) and button.is_enabled():
                button.click(timeout=2500)
                self.log(f"Нажата кнопка: {label}")
                return True
        except PlaywrightTimeoutError:
            pass
        except Exception as exc:
            self.log(f"Кнопка «{label}» недоступна: {exc}")
        return False

    def run_bot(self):
        try:
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            self.log("Запускаю Microsoft Edge…")
            with sync_playwright() as p:
                self.context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    channel="msedge",
                    headless=False,
                    viewport={"width": 1280, "height": 850},
                    args=["--start-maximized"],
                )
                page = self.context.pages[0] if self.context.pages else self.context.new_page()
                page.goto(GAME_URL, wait_until="domcontentloaded", timeout=60000)
                self.log("Страница игры открыта. Если потребуется — войди в аккаунт вручную.")
                self.log("Бот проверяет игровые кнопки; для работы нужна актуальная разметка сайта.")

                while not self.stop_event.is_set():
                    try:
                        frame = page.frame_locator("iframe#apps-game-frame")
                        self.click_button(frame, "#bt-play", "Играть")
                        time.sleep(0.6)
                        self.click_button(frame, "#bt-yes", "Подтвердить")
                        time.sleep(0.6)
                        self.click_button(frame, "#bt-spin", "Крутить бутылочку")
                    except Exception as exc:
                        self.log(f"Ожидание игрового элемента: {exc}")
                    for _ in range(16):
                        if self.stop_event.is_set():
                            break
                        time.sleep(0.25)
                self.log("Закрываю окно Edge…")
                self.context.close()
                self.context = None
        except Exception as exc:
            self.log(f"Ошибка: {exc}")
            self.log("Проверь, что Microsoft Edge установлен и доступен.")
        finally:
            self.context = None
            self.root.after(0, self.reset_buttons)

    def reset_buttons(self):
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def close(self):
        self.stop_event.set()
        self.root.after(300, self.root.destroy)

if __name__ == "__main__":
    root = tk.Tk()
    HuevoBottleEdgeApp(root)
    root.mainloop()
