from __future__ import annotations
import os, sys, time, tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HuevoHelper" / "browser-profile"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BASE_DIR / "playwright-browsers")

from playwright.sync_api import sync_playwright

APP_TITLE = "HuevoHelper"
DEFAULT_URL = "https://huevo.su/clicker"
MAX_CLICKS_PER_SESSION, MAX_CPS = 10000, 5
SCAN_SCRIPT = r"""() => {
 const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
 const label=e=>(e.innerText||e.getAttribute('aria-label')||e.getAttribute('title')||e.getAttribute('alt')||e.value||'').trim().replace(/\s+/g,' ').slice(0,100);
 return [...document.querySelectorAll('button,a[href],input,textarea,select,[role="button"]')].filter(visible).slice(0,300).map((e,i)=>{
 const tag=e.tagName.toLowerCase();let selector=e.id?'#'+CSS.escape(e.id):e.getAttribute('data-testid')?'[data-testid="'+CSS.escape(e.getAttribute('data-testid'))+'"]':tag+':nth-of-type('+( [...document.querySelectorAll(tag)].indexOf(e)+1)+')';
 return {index:i,tag,type:e.getAttribute('type')||'',label:label(e)||'(без подписи)',selector,disabled:!!e.disabled};
 });
}"""
class HuevoHelper:
 def __init__(self,root):
  self.root=root;root.title(APP_TITLE);root.geometry("380x300");root.resizable(False,False)
  self.browser=self.context=self.page=self.playwright=None;self.items=[];self.running=False
  self.lifetime=0;self.session_clicks=0;self.started_at=None;self.session_started=None
  self.show_main();root.protocol("WM_DELETE_WINDOW",self.close)
 def show_main(self):
  for c in self.root.winfo_children():c.destroy()
  self.root.geometry("1040x760");self.root.minsize(780,560)
  o=ttk.Frame(self.root,padding=12);o.pack(fill="both",expand=True)
  head=ttk.Frame(o);head.pack(fill="x");ttk.Label(head,text="HuevoHelper",font=("Segoe UI",16,"bold")).pack(side="left");ttk.Label(head,text="Локальный режим · без аккаунта").pack(side="right")
  ttk.Label(o,text="Выберите копилку на странице и нажмите «Старт автокликера».").pack(anchor="w",pady=(2,10))
  a=ttk.Frame(o);a.pack(fill="x",pady=(0,8));ttk.Label(a,text="Страница:").pack(side="left")
  self.url=tk.StringVar(value=DEFAULT_URL);ttk.Entry(a,textvariable=self.url).pack(side="left",fill="x",expand=True,padx=8)
  self.open_btn=ttk.Button(a,text="Открыть браузер",command=self.open_browser);self.open_btn.pack(side="left")
  self.goto_btn=ttk.Button(a,text="Перейти к clicker",command=self.go_clicker,state="disabled");self.goto_btn.pack(side="left",padx=(6,0))
  c=ttk.Frame(o);c.pack(fill="x",pady=(0,8))
  self.scan_btn=ttk.Button(c,text="Обновить элементы",command=self.scan,state="disabled");self.scan_btn.pack(side="left")
  self.one_btn=ttk.Button(c,text="Один клик",command=self.one_click,state="disabled");self.one_btn.pack(side="left",padx=6)
  self.start_btn=ttk.Button(c,text="▶ Старт автокликера",command=self.start,state="disabled");self.start_btn.pack(side="left")
  self.stop_btn=ttk.Button(c,text="■ Стоп",command=self.stop,state="disabled");self.stop_btn.pack(side="left",padx=6)
  self.status=tk.StringVar(value="Браузер не открыт");ttk.Label(c,textvariable=self.status).pack(side="right")
  stats=ttk.LabelFrame(o,text="Статистика",padding=8);stats.pack(fill="x",pady=(0,8))
  self.total=tk.StringVar(value=f"{self.lifetime:,}");self.session=tk.StringVar(value="0");self.rate=tk.StringVar(value="0.0 клика/с");self.elapsed=tk.StringVar(value="00:00:00")
  for i,(label,var) in enumerate([("Всего в базе",self.total),("В этой сессии",self.session),("Средняя скорость",self.rate),("Время работы",self.elapsed)]):
   cell=ttk.Frame(stats,padding=(6,2));cell.grid(row=0,column=i,sticky="ew");ttk.Label(cell,text=label).pack(anchor="w");ttk.Label(cell,textvariable=var,font=("Segoe UI",13,"bold")).pack(anchor="w");stats.columnconfigure(i,weight=1)
  cols=("tag","label","type","selector","state");self.tree=ttk.Treeview(o,columns=cols,show="headings",selectmode="browse",height=10)
  for col,title,width in [("tag","Тип",70),("label","Текст / подпись",260),("type","HTML type",90),("selector","Селектор",300),("state","Состояние",90)]:self.tree.heading(col,text=title);self.tree.column(col,width=width,minwidth=50,stretch=col in ("label","selector"))
  ys=ttk.Scrollbar(o,orient="vertical",command=self.tree.yview);xs=ttk.Scrollbar(o,orient="horizontal",command=self.tree.xview);self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set);self.tree.pack(fill="both",expand=True);ys.pack(side="right",fill="y");xs.pack(fill="x")
  lf=ttk.LabelFrame(o,text="Логи",padding=6);lf.pack(fill="both",expand=False,pady=(8,0));self.logs=tk.Text(lf,height=6,wrap="word",state="disabled");self.logs.pack(side="left",fill="both",expand=True);sb=ttk.Scrollbar(lf,orient="vertical",command=self.logs.yview);sb.pack(side="right",fill="y");self.logs.configure(yscrollcommand=sb.set)
  ttk.Label(o,text="Ограничение: до 5 кликов/с и 10 000 кликов за сессию. Сохраняются успешные действия браузера.",wraplength=980).pack(anchor="w",pady=(8,0))
 def log(self,msg):
  if not hasattr(self,"logs"):return
  self.logs.configure(state="normal");self.logs.insert("end",f"[{time.strftime('%H:%M:%S')}] {msg}\\n");self.logs.see("end");self.logs.configure(state="disabled")
 def open_browser(self):
  if self.context:
   try:
    if self.page and not self.page.is_closed():self.page.bring_to_front();return
   except Exception:pass
  u=self.url.get().strip();p=urlparse(u if "://" in u else "https://"+u)
  if p.scheme not in ("http","https") or not p.netloc:messagebox.showerror("Адрес","Введите корректный адрес.");return
  try:
   self.playwright=sync_playwright().start();self.context=self.playwright.chromium.launch_persistent_context(user_data_dir=str(USER_DATA_DIR),headless=False);self.browser=self.context.browser;self.page=self.context.pages[0] if self.context.pages else self.context.new_page();self.page.goto(p.geturl(),wait_until="domcontentloaded",timeout=60000)
   self.scan_btn.configure(state="normal");self.goto_btn.configure(state="normal");self.status.set("Браузер открыт");self.log("Открыта страница: "+p.geturl());self.scan()
  except Exception as e:self.log("Ошибка браузера: "+str(e));messagebox.showerror("Ошибка","Установите Chromium: py -m playwright install chromium\\n"+str(e)[:700]);self.dispose()
 def go_clicker(self):
  try:self.page.goto(DEFAULT_URL,wait_until="domcontentloaded",timeout=60000);self.url.set(DEFAULT_URL);self.scan()
  except Exception as e:messagebox.showerror("Ошибка перехода",str(e)[:700])
 def scan(self):
  if not self.page:return
  try:
   self.items=self.page.evaluate(SCAN_SCRIPT)
   for x in self.tree.get_children():self.tree.delete(x)
   for i,x in enumerate(self.items):self.tree.insert("","end",iid=str(i),values=(x["tag"],x["label"],x["type"],x["selector"],"отключён" if x["disabled"] else "доступен"))
   self.status.set(f"Найдено элементов: {len(self.items)}");self.one_btn.configure(state="normal" if self.items else "disabled");self.start_btn.configure(state="normal" if self.items and not self.running else "disabled");self.log(f"Найдено элементов: {len(self.items)}")
  except Exception as e:self.log("Ошибка чтения страницы: "+str(e))
 def selected(self):
  s=self.tree.selection()
  if not s:messagebox.showinfo("Выберите элемент","Сначала выберите строку.");return None
  x=self.items[int(s[0])]
  if x["disabled"]:messagebox.showwarning("Элемент отключён","Выбранный элемент отключён.");return None
  return x
 def one_click(self):
  x=self.selected()
  if x:
   try:self.page.locator(x["selector"]).first.click(timeout=5000);self.session_clicks+=1;self.refresh_stats();self.log(f"Один клик: {x['label']}")
   except Exception as e:messagebox.showerror("Ошибка клика",str(e)[:700])
 def start(self):
  if self.running:return
  x=self.selected()
  if not x:return
  if not messagebox.askyesno("Запустить автокликер?",f"Элемент: {x['label']}\\nДо {MAX_CPS} кликов/с; лимит {MAX_CLICKS_PER_SESSION}. Продолжить?"):return
  self.active=x;self.running=True;self.started_at=time.monotonic();self.session_started=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime());self.session_clicks=0
  self.start_btn.configure(state="disabled");self.stop_btn.configure(state="normal");self.scan_btn.configure(state="disabled");self.one_btn.configure(state="disabled");self.status.set("Автокликер работает");self.log("Автокликер запущен");self.tick()
 def tick(self):
  if not self.running:return
  if self.session_clicks>=MAX_CLICKS_PER_SESSION:self.stop("Достигнут лимит сессии.");return
  try:
   self.page.locator(self.active["selector"]).first.click(timeout=1500);self.session_clicks+=1
   if self.session_clicks==1 or self.session_clicks%10==0:self.log(f"Кликов в сессии: {self.session_clicks}")
   self.refresh_stats();self.root.after(round(1000/MAX_CPS),self.tick)
  except Exception as e:self.stop("Ошибка клика: "+str(e));messagebox.showwarning("Остановлено","Элемент не найден. Обновите список и выберите его снова.")
 def stop(self,reason="Остановлено пользователем."):
  was=self.running;self.running=False
  if hasattr(self,"stop_btn"):self.stop_btn.configure(state="disabled")
  if hasattr(self,"start_btn"):self.start_btn.configure(state="normal" if self.items else "disabled")
  if hasattr(self,"scan_btn"):self.scan_btn.configure(state="normal" if self.page else "disabled")
  if hasattr(self,"one_btn"):self.one_btn.configure(state="normal" if self.items else "disabled")
  if hasattr(self,"status"):self.status.set("Автокликер остановлен")
  if was:
   self.log(f"{reason} Клики: {self.session_clicks}");self.save_session()
  self.refresh_stats()
 def save_session(self):
  if self.session_started:
   self.lifetime += self.session_clicks
   self.log("Сессия завершена. Облачная статистика отключена.")
 def refresh_stats(self):
  if not hasattr(self,"total"):return
  self.total.set(f"{(self.lifetime+self.session_clicks) if self.running else self.lifetime:,}");self.session.set(f"{self.session_clicks:,}");d=max(0,time.monotonic()-(self.started_at or time.monotonic()));self.elapsed.set(time.strftime("%H:%M:%S",time.gmtime(d)));self.rate.set(f"{self.session_clicks/d:.1f} клика/с" if d else "0.0 клика/с")
 def dispose(self):
  for obj,method in ((self.context,"close"),(self.browser,"close"),(self.playwright,"stop")):
   try:
    if obj:getattr(obj,method)()
   except Exception:pass
  self.context=self.browser=self.playwright=self.page=None
 def close(self):
  self.stop("Приложение закрывается.");self.dispose();self.root.destroy()

if __name__=="__main__":
 root=tk.Tk()
 try:ttk.Style().theme_use("vista")
 except tk.TclError:pass
 HuevoHelper(root);root.mainloop()
