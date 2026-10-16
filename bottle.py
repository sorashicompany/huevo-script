from __future__ import annotations
import os, time, subprocess, tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from playwright.sync_api import sync_playwright

APP_TITLE = "хуевая бутылочка"
BOTTLE_URL = "https://huevo.su/apps/"
BOTTLE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HuevoHelper" / "bottle-profile"

class BottleApp:
 def __init__(self, root):
  self.root=root; root.title(APP_TITLE); root.geometry("500x300"); root.minsize(430,250)
  self.browser=self.context=self.page=self.playwright=self.chrome_process=None
  self.running=False; self.after_id=None; self.clicks=0
  o=ttk.Frame(root,padding=16); o.pack(fill="both",expand=True)
  ttk.Label(o,text=APP_TITLE,font=("Segoe UI",17,"bold")).pack(anchor="w")
  ttk.Label(o,text="Автонажатия кнопок игры в бутылочку на huevo.su.").pack(anchor="w",pady=(4,14))
  row=ttk.Frame(o); row.pack(fill="x",pady=(0,12))
  ttk.Button(row,text="Открыть бутылочку",command=self.open_browser).pack(side="left")
  self.auto_btn=ttk.Button(row,text="Автонажатия: Старт",command=self.toggle_auto,state="disabled"); self.auto_btn.pack(side="left",padx=8)
  self.status=tk.StringVar(value="Браузер игры не открыт")
  ttk.Label(o,textvariable=self.status,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=(0,10))
  stats=ttk.LabelFrame(o,text="Статистика",padding=10); stats.pack(fill="x")
  self.click_count=tk.StringVar(value="0")
  ttk.Label(stats,text="Выполнено нажатий:").pack(side="left")
  ttk.Label(stats,textvariable=self.click_count,font=("Segoe UI",13,"bold")).pack(side="left",padx=8)
  lf=ttk.LabelFrame(o,text="Логи",padding=6); lf.pack(fill="both",expand=True,pady=(12,0))
  self.logs=tk.Text(lf,height=5,wrap="word",state="disabled"); self.logs.pack(side="left",fill="both",expand=True)
  sb=ttk.Scrollbar(lf,orient="vertical",command=self.logs.yview); sb.pack(side="right",fill="y"); self.logs.configure(yscrollcommand=sb.set)
  root.protocol("WM_DELETE_WINDOW",self.close)
 def log(self,msg):
  self.logs.configure(state="normal"); self.logs.insert("end",f"[{time.strftime('%H:%M:%S')}] {msg}\n"); self.logs.see("end"); self.logs.configure(state="disabled")
 def locate_chrome(self):
  local=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))
  paths=[local/"Google"/"Chrome"/"Application"/"chrome.exe",Path(os.environ.get("PROGRAMFILES",r"C:\Program Files"))/"Google"/"Chrome"/"Application"/"chrome.exe",Path(os.environ.get("PROGRAMFILES(X86)",r"C:\Program Files (x86)"))/"Google"/"Chrome"/"Application"/"chrome.exe"]
  return next((p for p in paths if p.is_file()),None)
 def open_browser(self):
  if self.page:
   try:
    if not self.page.is_closed(): self.page.bring_to_front(); return
   except Exception: pass
  BOTTLE_DIR.mkdir(parents=True,exist_ok=True); port_file=BOTTLE_DIR/"DevToolsActivePort"
  try: port_file.unlink(missing_ok=True)
  except OSError: pass
  try:
   chrome=self.locate_chrome()
   if not chrome: raise FileNotFoundError("Google Chrome не найден. Установи Google Chrome.")
   self.chrome_process=subprocess.Popen([str(chrome),"--remote-debugging-port=0",f"--user-data-dir={BOTTLE_DIR}","--no-first-run","--no-default-browser-check",BOTTLE_URL],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   deadline=time.monotonic()+20
   while time.monotonic()<deadline and not port_file.exists():
    if self.chrome_process.poll() is not None: raise RuntimeError("Chrome завершился до запуска.")
    time.sleep(.2)
   if not port_file.exists(): raise TimeoutError("Chrome не открыл интерфейс управления за 20 секунд.")
   port=port_file.read_text(encoding="utf-8").splitlines()[0].strip()
   self.playwright=sync_playwright().start(); self.browser=self.playwright.chromium.connect_over_cdp("http://127.0.0.1:"+port)
   if not self.browser.contexts: raise RuntimeError("Вкладки Chrome недоступны.")
   self.context=self.browser.contexts[0]; self.page=self.context.pages[0] if self.context.pages else self.context.new_page()
   if self.page.url=="about:blank": self.page.goto(BOTTLE_URL,wait_until="domcontentloaded",timeout=60000)
   self.auto_btn.configure(state="normal"); self.status.set("Бутылочка открыта — автонажатия выключены"); self.log("Браузер бутылочки открыт")
  except Exception as e:
   self.log("Ошибка запуска: "+str(e)); messagebox.showerror("Ошибка запуска Chrome",str(e)[:600]); self.dispose()
 def toggle_auto(self):
  if not self.page: messagebox.showinfo("Бутылочка","Сначала нажми «Открыть бутылочку»."); return
  self.running=not self.running
  if self.running:
   self.auto_btn.configure(text="Автонажатия: Стоп"); self.status.set("Автонажатия включены — ожидание кнопок"); self.log("Автонажатия включены"); self.tick()
  else:
   if self.after_id:
    try: self.root.after_cancel(self.after_id)
    except Exception: pass
    self.after_id=None
   self.auto_btn.configure(text="Автонажатия: Старт"); self.status.set("Автонажатия выключены"); self.log("Автонажатия выключены")
 def tick(self):
  if not self.running or not self.page: return
  try:
   frame=self.page.frame_locator("iframe#apps-game-frame"); yes=frame.locator("#bt-yes"); spin=frame.locator("#bt-spin")
   if yes.count() and yes.is_visible() and yes.is_enabled(): yes.click(timeout=1500); self.clicked("Поцеловать")
   elif spin.count() and spin.is_visible() and spin.is_enabled(): spin.click(timeout=1500); self.clicked("Крутить бутылочку")
   self.after_id=self.root.after(250,self.tick)
  except Exception: self.after_id=self.root.after(500,self.tick)
 def clicked(self,label):
  self.clicks+=1; self.click_count.set(str(self.clicks)); self.log("Нажато «"+label+"»")
 def dispose(self):
  self.running=False
  if self.after_id:
   try: self.root.after_cancel(self.after_id)
   except Exception: pass
   self.after_id=None
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
  self.browser=self.context=self.playwright=self.page=self.chrome_process=None
 def close(self):
  self.dispose(); self.root.destroy()

if __name__=="__main__":
 root=tk.Tk()
 try: ttk.Style().theme_use("vista")
 except tk.TclError: pass
 BottleApp(root); root.mainloop()
