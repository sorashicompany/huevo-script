from __future__ import annotations
import os, sys, time, subprocess, tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

APP_TITLE = "хуевый автокликер"
DEFAULT_URL = "https://huevo.su/clicker"
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HuevoHelper" / "browser-profile"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
TARGET_SELECTOR = "#ck-cat"
MIN_INTERVAL_MS = 20

class HuevoHelper:
 def __init__(self, root):
  self.root=root
  root.title(APP_TITLE); root.geometry("620x510"); root.minsize(560,450); root.resizable(True,True)
  self.browser=self.context=self.page=self.playwright=None; self.chrome_process=None
  self.bottle_browser=self.bottle_context=self.bottle_page=self.bottle_playwright=None; self.bottle_process=None
  self.bottle_running=False; self.bottle_after_id=None
  self.running=False; self.session_clicks=0; self.total_clicks=0; self.started_at=None; self.after_id=None
  self.show_main(); root.protocol("WM_DELETE_WINDOW",self.close)
 def show_main(self):
  o=ttk.Frame(self.root,padding=14); o.pack(fill="both",expand=True)
  ttk.Label(o,text=APP_TITLE,font=("Segoe UI",17,"bold")).pack(anchor="w")
  ttk.Label(o,text="Автоматически кликает по коту-копилке. Работает, пока приложение запущено.").pack(anchor="w",pady=(2,12))
  a=ttk.Frame(o); a.pack(fill="x",pady=(0,8))
  ttk.Label(a,text="Страница:").pack(side="left")
  self.url=tk.StringVar(value=DEFAULT_URL)
  ttk.Entry(a,textvariable=self.url).pack(side="left",fill="x",expand=True,padx=8)
  self.open_btn=ttk.Button(a,text="Открыть браузер",command=self.open_browser); self.open_btn.pack(side="left")
  self.goto_btn=ttk.Button(o,text="Перейти к clicker",command=self.go_clicker,state="disabled"); self.goto_btn.pack(anchor="w",pady=(0,8))
  bottle=ttk.LabelFrame(o,text="Игра в бутылочку",padding=8); bottle.pack(fill="x",pady=(0,10))
  br=ttk.Frame(bottle); br.pack(fill="x")
  self.bottle_open_btn=ttk.Button(br,text="Открыть бутылочку",command=self.open_bottle); self.bottle_open_btn.pack(side="left")
  self.bottle_auto_btn=ttk.Button(br,text="Автонажатия: Старт",command=self.toggle_bottle_auto,state="disabled"); self.bottle_auto_btn.pack(side="left",padx=8)
  self.bottle_status=tk.StringVar(value="Браузер игры не открыт")
  ttk.Label(bottle,textvariable=self.bottle_status).pack(anchor="w",pady=(6,0))
  settings=ttk.LabelFrame(o,text="Настройки автокликера",padding=10); settings.pack(fill="x",pady=(0,10))
  row=ttk.Frame(settings); row.pack(fill="x")
  ttk.Label(row,text="Интервал (мс):").pack(side="left")
  self.interval=tk.StringVar(value="200")
  ttk.Entry(row,textvariable=self.interval,width=10).pack(side="left",padx=(6,18))
  ttk.Label(row,text="Количество повторений:").pack(side="left")
  self.repetitions=tk.StringVar(value="")
  ttk.Entry(row,textvariable=self.repetitions,width=12).pack(side="left",padx=6)
  ttk.Label(settings,text="Оставь количество пустым для бесконечных повторений. Минимальный интервал — 20 мс.").pack(anchor="w",pady=(8,0))
  controls=ttk.Frame(o); controls.pack(fill="x",pady=(0,10))
  self.one_btn=ttk.Button(controls,text="Один клик",command=self.one_click,state="disabled"); self.one_btn.pack(side="left")
  self.start_btn=ttk.Button(controls,text="▶ Старт",command=self.start,state="disabled"); self.start_btn.pack(side="left",padx=8)
  self.stop_btn=ttk.Button(controls,text="■ Стоп",command=self.stop,state="disabled"); self.stop_btn.pack(side="left")
  self.status=tk.StringVar(value="Браузер не открыт")
  ttk.Label(o,textvariable=self.status,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(0,10))
  stats=ttk.LabelFrame(o,text="Статистика",padding=8); stats.pack(fill="x",pady=(0,10))
  self.session=tk.StringVar(value="0"); self.total=tk.StringVar(value="0"); self.elapsed=tk.StringVar(value="00:00:00")
  for i,(label,var) in enumerate([("Клики в запуске",self.session),("Кликов всего",self.total),("Время работы",self.elapsed)]):
   cell=ttk.Frame(stats,padding=4); cell.grid(row=0,column=i,sticky="ew"); ttk.Label(cell,text=label).pack(anchor="w"); ttk.Label(cell,textvariable=var,font=("Segoe UI",13,"bold")).pack(anchor="w"); stats.columnconfigure(i,weight=1)
  lf=ttk.LabelFrame(o,text="Логи",padding=6); lf.pack(fill="both",expand=True)
  self.logs=tk.Text(lf,height=6,wrap="word",state="disabled"); self.logs.pack(side="left",fill="both",expand=True)
  sb=ttk.Scrollbar(lf,orient="vertical",command=self.logs.yview); sb.pack(side="right",fill="y"); self.logs.configure(yscrollcommand=sb.set)
 def log(self,msg):
  if not hasattr(self,"logs"): return
  self.logs.configure(state="normal"); self.logs.insert("end",f"[{time.strftime('%H:%M:%S')}] {msg}\n"); self.logs.see("end"); self.logs.configure(state="disabled")
 def locate_chrome(self):
  local=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))
  candidates=[local/"Google"/"Chrome"/"Application"/"chrome.exe",
   Path(os.environ.get("PROGRAMFILES",r"C:\Program Files"))/"Google"/"Chrome"/"Application"/"chrome.exe",
   Path(os.environ.get("PROGRAMFILES(X86)",r"C:\Program Files (x86)"))/"Google"/"Chrome"/"Application"/"chrome.exe"]
  return next((x for x in candidates if x.is_file()),None)
 def open_browser(self):
  if self.page:
   try:
    if not self.page.is_closed(): self.page.bring_to_front(); return
   except Exception: pass
  u=self.url.get().strip(); p=urlparse(u if "://" in u else "https://"+u)
  if p.scheme not in ("http","https") or not p.netloc:
   messagebox.showerror("Адрес","Введите корректный адрес."); return
  try:
   chrome=self.locate_chrome()
   if not chrome: raise FileNotFoundError("Google Chrome не найден. Установи обычный Google Chrome.")
   port_file=USER_DATA_DIR/"DevToolsActivePort"
   try: port_file.unlink(missing_ok=True)
   except OSError: pass
   args=[str(chrome),"--remote-debugging-port=0",f"--user-data-dir={USER_DATA_DIR}","--no-first-run","--no-default-browser-check",p.geturl()]
   self.chrome_process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   deadline=time.monotonic()+20
   while time.monotonic()<deadline and not port_file.exists():
    if self.chrome_process.poll() is not None: raise RuntimeError("Chrome завершился до запуска удалённого интерфейса.")
    time.sleep(.2)
   if not port_file.exists(): raise TimeoutError("Chrome не открыл локальный интерфейс управления за 20 секунд.")
   port=port_file.read_text(encoding="utf-8").splitlines()[0].strip()
   self.playwright=sync_playwright().start()
   self.browser=self.playwright.chromium.connect_over_cdp("http://127.0.0.1:"+port)
   if not self.browser.contexts: raise RuntimeError("Вкладки Chrome недоступны.")
   self.context=self.browser.contexts[0]
   self.page=self.context.pages[0] if self.context.pages else self.context.new_page()
   if self.page.url=="about:blank": self.page.goto(p.geturl(),wait_until="domcontentloaded",timeout=60000)
   self.goto_btn.configure(state="normal"); self.log("Chrome подключён: "+p.geturl()); self.check_target()
  except Exception as e:
   self.log("Ошибка браузера: "+str(e)); messagebox.showerror("Ошибка запуска Chrome",str(e)[:600]); self.dispose()
 def open_bottle(self):
  if self.bottle_page:
   try:
    if not self.bottle_page.is_closed():
     self.bottle_page.bring_to_front()
     return
   except Exception: pass
  bottle_dir=Path(os.environ.get("LOCALAPPDATA",str(Path.home()))) / "HuevoHelper" / "bottle-profile"
  bottle_dir.mkdir(parents=True,exist_ok=True)
  port_file=bottle_dir/"DevToolsActivePort"
  try: port_file.unlink(missing_ok=True)
  except OSError: pass
  try:
   chrome=self.locate_chrome()
   if not chrome: raise FileNotFoundError("Google Chrome не найден. Установи обычный Google Chrome.")
   args=[str(chrome),"--remote-debugging-port=0",f"--user-data-dir={bottle_dir}","--no-first-run","--no-default-browser-check","https://huevo.su/apps/"]
   self.bottle_process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   deadline=time.monotonic()+20
   while time.monotonic()<deadline and not port_file.exists():
    if self.bottle_process.poll() is not None: raise RuntimeError("Chrome для бутылочки завершился до запуска.")
    time.sleep(.2)
   if not port_file.exists(): raise TimeoutError("Chrome для бутылочки не открыл интерфейс управления за 20 секунд.")
   port=port_file.read_text(encoding="utf-8").splitlines()[0].strip()
   self.bottle_playwright=sync_playwright().start()
   self.bottle_browser=self.bottle_playwright.chromium.connect_over_cdp("http://127.0.0.1:"+port)
   if not self.bottle_browser.contexts: raise RuntimeError("Вкладки браузера бутылочки недоступны.")
   self.bottle_context=self.bottle_browser.contexts[0]
   self.bottle_page=self.bottle_context.pages[0] if self.bottle_context.pages else self.bottle_context.new_page()
   if self.bottle_page.url=="about:blank": self.bottle_page.goto("https://huevo.su/apps/",wait_until="domcontentloaded",timeout=60000)
   self.bottle_auto_btn.configure(state="normal")
   self.bottle_status.set("Бутылочка открыта — автонажатия выключены")
   self.log("Открыт отдельный браузер для игры в бутылочку")
  except Exception as e:
   self.log("Ошибка запуска бутылочки: "+str(e))
   messagebox.showerror("Ошибка запуска бутылочки",str(e)[:600])
   self.dispose_bottle()

 def toggle_bottle_auto(self):
  if not self.bottle_page:
   messagebox.showinfo("Бутылочка","Сначала нажми «Открыть бутылочку».")
   return
  self.bottle_running=not self.bottle_running
  if self.bottle_running:
   self.bottle_auto_btn.configure(text="Автонажатия: Стоп")
   self.bottle_status.set("Автонажатия включены — ожидание кнопок игры")
   self.log("Автонажатия в бутылочке включены")
   self.bottle_tick()
  else:
   if self.bottle_after_id:
    try: self.root.after_cancel(self.bottle_after_id)
    except Exception: pass
    self.bottle_after_id=None
   self.bottle_auto_btn.configure(text="Автонажатия: Старт")
   self.bottle_status.set("Автонажатия выключены")
   self.log("Автонажатия в бутылочке выключены")

 def bottle_tick(self):
  if not self.bottle_running or not self.bottle_page: return
  try:
   frame=self.bottle_page.frame_locator("iframe#apps-game-frame")
   yes=frame.locator("#bt-yes")
   spin=frame.locator("#bt-spin")
   if yes.count() and yes.is_visible() and yes.is_enabled():
    yes.click(timeout=1500)
    self.log("Бутылочка: нажато «Поцеловать»")
   elif spin.count() and spin.is_visible() and spin.is_enabled():
    spin.click(timeout=1500)
    self.log("Бутылочка: нажато «Крутить бутылочку»")
   self.bottle_after_id=self.root.after(250,self.bottle_tick)
  except Exception:
   # The game iframe may be reloading between rounds; keep polling while enabled.
   self.bottle_after_id=self.root.after(500,self.bottle_tick)

 def dispose_bottle(self):
  self.bottle_running=False
  if self.bottle_after_id:
   try: self.root.after_cancel(self.bottle_after_id)
   except Exception: pass
   self.bottle_after_id=None
  try:
   if self.bottle_browser: self.bottle_browser.close()
  except Exception: pass
  try:
   if self.bottle_playwright: self.bottle_playwright.stop()
  except Exception: pass
  try:
   if self.bottle_process and self.bottle_process.poll() is None:
    self.bottle_process.terminate()
    try: self.bottle_process.wait(timeout=3)
    except subprocess.TimeoutExpired: self.bottle_process.kill()
  except Exception: pass
  self.bottle_browser=self.bottle_context=self.bottle_playwright=self.bottle_page=self.bottle_process=None

 def go_clicker(self):
  try:
   self.page.goto(DEFAULT_URL,wait_until="domcontentloaded",timeout=60000); self.url.set(DEFAULT_URL); self.check_target()
  except Exception as e: messagebox.showerror("Ошибка перехода",str(e)[:700])
 def check_target(self):
  if not self.page: return
  try:
   found=self.page.locator(TARGET_SELECTOR).count()>0
   if found:
    self.status.set("Кот-копилка найден — готов к запуску")
    self.one_btn.configure(state="normal"); self.start_btn.configure(state="normal" if not self.running else "disabled")
    self.log("Кот-копилка выбран автоматически (#ck-cat)")
   else:
    self.status.set("Кот не найден. Открой страницу clicker и нажми «Перейти к clicker».")
    self.one_btn.configure(state="disabled"); self.start_btn.configure(state="disabled")
    self.root.after(1500,self.check_target)
  except Exception as e:
   self.status.set("Ожидание загрузки кота…")
   if self.page and not self.running: self.root.after(1500,self.check_target)
 def click_cat(self):
  # Use Playwright's mouse input rather than HTMLElement.click(): the site may ignore
  # synthetic DOM clicks (event.isTrusted is false). Force bypasses overlay/actionability checks.
  target=self.page.locator(TARGET_SELECTOR).first
  if target.count()==0:
   return False
  target.click(force=True, timeout=3000)
  return True
 def one_click(self):
  try:
   if not self.page or not self.click_cat(): raise RuntimeError("Кот-копилка не найден на странице.")
   self.log("Выполнен один клик")
  except Exception as e: messagebox.showerror("Ошибка клика",str(e)[:600])
 def start(self):
  if self.running: return
  try:
   interval=int(self.interval.get().strip())
   if interval<MIN_INTERVAL_MS: raise ValueError(f"Интервал должен быть не меньше {MIN_INTERVAL_MS} мс.")
   raw=self.repetitions.get().strip()
   repeats=None if raw=="" else int(raw)
   if repeats is not None and repeats<1: raise ValueError("Количество повторений должно быть положительным числом или пустым.")
  except ValueError as e: messagebox.showerror("Проверь настройки",str(e) if str(e).startswith("Интервал") or str(e).startswith("Количество") else "Интервал и повторения должны быть целыми числами."); return
  if not self.page: messagebox.showinfo("Браузер","Сначала нажми «Открыть браузер»."); return
  try:
   if self.page.locator(TARGET_SELECTOR).count()==0: self.check_target(); messagebox.showwarning("Кот не найден","Открой huevo.su/clicker и дождись загрузки кота."); return
  except Exception as e: messagebox.showerror("Ошибка страницы",str(e)[:500]); return
  self.interval_ms=interval; self.repeat_limit=repeats; self.running=True; self.session_clicks=0; self.started_at=time.monotonic()
  self.session.set("0"); self.elapsed.set("00:00:00")
  self.start_btn.configure(state="disabled"); self.one_btn.configure(state="disabled"); self.stop_btn.configure(state="normal")
  self.status.set("Автокликер работает — можно свернуть Chrome"); self.log(f"Старт: интервал {interval} мс, повторений: {repeats if repeats is not None else 'бесконечно'}")
  self.tick()
 def tick(self):
  if not self.running: return
  if self.repeat_limit is not None and self.session_clicks>=self.repeat_limit:
   self.stop("Заданное количество повторений выполнено."); return
  try:
   if not self.click_cat(): raise RuntimeError("Кот-копилка #ck-cat не найден.")
   self.session_clicks+=1; self.session.set(str(self.session_clicks)); self.total.set(str(self.session_clicks))
   elapsed=max(0,time.monotonic()-self.started_at); self.elapsed.set(time.strftime("%H:%M:%S",time.gmtime(elapsed)))
   if self.session_clicks==1 or self.session_clicks%25==0: self.log(f"Кликов: {self.session_clicks}")
   self.after_id=self.root.after(self.interval_ms,self.tick)
  except Exception as e:
   self.stop("Ошибка клика: "+str(e)); messagebox.showwarning("Автокликер остановлен","Не удалось кликнуть по коту. Проверь, что вкладка открыта и сайт не изменился.")
 def stop(self,reason="Остановлено пользователем."):
  was=self.running; self.running=False
  if self.after_id:
   try: self.root.after_cancel(self.after_id)
   except Exception: pass
   self.after_id=None
  self.stop_btn.configure(state="disabled")
  self.start_btn.configure(state="normal" if self.page and not self.running else "disabled")
  self.one_btn.configure(state="normal" if self.page and not self.running else "disabled")
  if was: self.log(f"{reason} Клики: {self.session_clicks}")
  if self.page:
   try: self.status.set("Кот-копилка найден — готов к запуску" if self.page.locator(TARGET_SELECTOR).count() else "Кот не найден")
   except Exception: self.status.set("Автокликер остановлен")
 def dispose(self):
  try:
   if self.browser: self.browser.close()
  except Exception: pass
  try:
   if self.playwright: self.playwright.stop()
  except Exception: pass
  try:
   if self.chrome_process and self.chrome_process.poll() is None:
    self.chrome_process.terminate()
    try: self.chrome_process.wait(timeout=3)
    except subprocess.TimeoutExpired: self.chrome_process.kill()
  except Exception: pass
  self.context=self.browser=self.playwright=self.page=self.chrome_process=None
 def close(self):
  self.stop("Приложение закрывается."); self.dispose_bottle(); self.dispose(); self.root.destroy()

if __name__=="__main__":
 root=tk.Tk()
 try: ttk.Style().theme_use("vista")
 except tk.TclError: pass
 HuevoHelper(root); root.mainloop()
