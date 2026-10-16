from __future__ import annotations
import base64, hashlib, json, secrets, threading, time, tkinter as tk, urllib.error, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from tkinter import messagebox, ttk
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

APP_TITLE = "HuevoHelper"
DEFAULT_URL = "https://huevo.su/clicker"
SUPABASE_URL = "https://hzcexklqkpgkdbpzdhfx.supabase.co"
SUPABASE_KEY = "sb_publishable_tsaQooSI0G7aj7ZZaFyQBA_5noPmoSw"
OAUTH_REDIRECT = "http://127.0.0.1:8765/callback"
MAX_CLICKS_PER_SESSION, MAX_CPS = 10000, 5
SCAN_SCRIPT = r"""() => {
 const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
 const label=e=>(e.innerText||e.getAttribute('aria-label')||e.getAttribute('title')||e.getAttribute('alt')||e.value||'').trim().replace(/\\s+/g,' ').slice(0,100);
 return [...document.querySelectorAll('button,a[href],input,textarea,select,[role="button"]')].filter(visible).slice(0,300).map((e,i)=>{
 const tag=e.tagName.toLowerCase();let selector=e.id?'#'+CSS.escape(e.id):e.getAttribute('data-testid')?'[data-testid="'+CSS.escape(e.getAttribute('data-testid'))+'"]':tag+':nth-of-type('+( [...document.querySelectorAll(tag)].indexOf(e)+1)+')';
 return {index:i,tag,type:e.getAttribute('type')||'',label:label(e)||'(без подписи)',selector,disabled:!!e.disabled};
 });
}"""
def api(path, method="GET", token=None, body=None, query=""):
 url=SUPABASE_URL+path+query
 data=None if body is None else json.dumps(body).encode()
 headers={"apikey":SUPABASE_KEY,"Content-Type":"application/json"}
 if token: headers["Authorization"]="Bearer "+token
 req=urllib.request.Request(url,data=data,headers=headers,method=method)
 try:
  with urllib.request.urlopen(req,timeout=20) as r:
   raw=r.read().decode();return json.loads(raw) if raw else {}
 except urllib.error.HTTPError as e: raise RuntimeError(f"Supabase HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from e

class HuevoHelper:
 def __init__(self,root):
  self.root=root;root.title(APP_TITLE);root.geometry("380x300");root.resizable(False,False)
  self.user=None;self.token=None;self.refresh_token=None;self.server=None;self.verifier=None
  self.browser=self.context=self.page=self.playwright=None;self.items=[];self.running=False
  self.lifetime=0;self.session_clicks=0;self.started_at=None;self.session_started=None
  self.show_login();root.protocol("WM_DELETE_WINDOW",self.close)
 def show_login(self):
  for c in self.root.winfo_children():c.destroy()
  self.root.geometry("380x300");self.root.resizable(False,False)
  f=ttk.Frame(self.root,padding=24);f.pack(fill="both",expand=True)
  ttk.Label(f,text="🐱 HuevoHelper",font=("Segoe UI",19,"bold")).pack(pady=(8,4))
  ttk.Label(f,text="Войдите, чтобы открыть автокликер").pack(pady=(0,18))
  self.login_btn=ttk.Button(f,text="G   Продолжить с Google",command=self.google_login);self.login_btn.pack(fill="x",ipady=8)
  ttk.Label(f,text="Безопасный вход через Supabase Auth").pack(pady=12)
  self.login_status=tk.StringVar(value="Готово к входу");ttk.Label(f,textvariable=self.login_status,wraplength=300).pack()
 def google_login(self):
  self.login_btn.configure(state="disabled");self.login_status.set("Открываем Google…")
  try:
   self.verifier=secrets.token_urlsafe(48)
   challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
   app=self
   class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
     p=urllib.parse.parse_qs(urlparse(self.path).query);code=p.get("code",[None])[0];err=p.get("error_description",p.get("error",["OAuth отменён"]))[0]
     self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.end_headers()
     self.wfile.write(("Вход завершён. Вернитесь в HuevoHelper." if code else "Вход не выполнен. Вернитесь в HuevoHelper.").encode())
     if code: threading.Thread(target=app.exchange,args=(code,),daemon=True).start()
     else: app.root.after(0,lambda:app.oauth_failed(str(err)))
    def log_message(self,*args):pass
   self.server=HTTPServer(("127.0.0.1",8765),Handler)
   threading.Thread(target=self.server.serve_forever,daemon=True).start()
   q=urllib.parse.urlencode({"provider":"google","redirect_to":OAUTH_REDIRECT,"code_challenge":challenge,"code_challenge_method":"s256"})
   webbrowser.open(SUPABASE_URL+"/auth/v1/authorize?"+q)
   self.login_status.set("Завершите вход в браузере, затем вернитесь сюда.")
  except Exception as e:self.oauth_failed(str(e))
 def exchange(self,code):
  try:
   s=api("/auth/v1/token?grant_type=pkce","POST",body={"auth_code":code,"code_verifier":self.verifier})
   self.token=s["access_token"];self.refresh_token=s.get("refresh_token");self.user=s.get("user",{})
   self.root.after(0,self.login_succeeded)
  except Exception as e:self.root.after(0,lambda:self.oauth_failed(str(e)))
 def stop_server(self):
  if self.server:
   try:self.server.shutdown();self.server.server_close()
   except Exception:pass
   self.server=None
 def oauth_failed(self,err):
  if hasattr(self,"login_status"):self.login_status.set("Вход не выполнен. Проверьте настройки OAuth.")
  if hasattr(self,"login_btn"):self.login_btn.configure(state="normal")
  messagebox.showerror("Ошибка входа","Google OAuth требует настроек в Supabase Dashboard.\\n\\n"+err[:700],parent=self.root)
  self.stop_server()
 def login_succeeded(self):
  self.stop_server();meta=self.user.get("user_metadata") or {};email=self.user.get("email","")
  profile={"user_id":self.user["id"],"email":email,"display_name":meta.get("full_name") or meta.get("name") or email,"avatar_url":meta.get("avatar_url") or meta.get("picture")}
  try:api("/rest/v1/user_profiles?on_conflict=user_id","POST",self.token,profile,"&on_conflict=user_id")
  except Exception as e: print("Profile save:",e)
  try:self.lifetime=sum(int(r.get("click_count",0)) for r in api("/rest/v1/click_sessions",token=self.token,query="?select=click_count&limit=500"))
  except Exception:self.lifetime=0
  self.show_main();self.log("Вход выполнен: "+(email or "Google"));self.log(f"Загружено из Supabase: {self.lifetime:,} кликов")
 def show_main(self):
  for c in self.root.winfo_children():c.destroy()
  self.root.geometry("1040x760");self.root.minsize(780,560)
  o=ttk.Frame(self.root,padding=12);o.pack(fill="both",expand=True)
  head=ttk.Frame(o);head.pack(fill="x");ttk.Label(head,text="HuevoHelper",font=("Segoe UI",16,"bold")).pack(side="left");ttk.Label(head,text=self.user.get("email","Google")).pack(side="right")
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
  if self.browser:
   try:
    if self.page and not self.page.is_closed():self.page.bring_to_front();return
   except Exception:pass
  u=self.url.get().strip();p=urlparse(u if "://" in u else "https://"+u)
  if p.scheme not in ("http","https") or not p.netloc:messagebox.showerror("Адрес","Введите корректный адрес.");return
  try:
   self.playwright=sync_playwright().start();self.browser=self.playwright.chromium.launch(headless=False);self.context=self.browser.new_context();self.page=self.context.new_page();self.page.goto(p.geturl(),wait_until="domcontentloaded",timeout=60000)
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
  if not self.token or not self.user or not self.session_started:return
  payload={"user_id":self.user["id"],"started_at":self.session_started,"ended_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"click_count":self.session_clicks,"duration_seconds":max(0,int(time.monotonic()-(self.started_at or time.monotonic())))}
  try:api("/rest/v1/click_sessions","POST",self.token,payload);self.lifetime+=self.session_clicks;self.log("Статистика сохранена в Supabase")
  except Exception as e:self.log("Ошибка сохранения статистики: "+str(e))
 def refresh_stats(self):
  if not hasattr(self,"total"):return
  self.total.set(f"{self.lifetime+self.session_clicks:,}");self.session.set(f"{self.session_clicks:,}");d=max(0,time.monotonic()-(self.started_at or time.monotonic()));self.elapsed.set(time.strftime("%H:%M:%S",time.gmtime(d)));self.rate.set(f"{self.session_clicks/d:.1f} клика/с" if d else "0.0 клика/с")
 def dispose(self):
  for obj,method in ((self.context,"close"),(self.browser,"close"),(self.playwright,"stop")):
   try:
    if obj:getattr(obj,method)()
   except Exception:pass
  self.context=self.browser=self.playwright=self.page=None
 def close(self):
  self.stop("Приложение закрывается.");self.stop_server();self.dispose();self.root.destroy()

if __name__=="__main__":
 root=tk.Tk()
 try:ttk.Style().theme_use("vista")
 except tk.TclError:pass
 HuevoHelper(root);root.mainloop()
