HuevoHelper
===========

Windows desktop clicker helper with a compact Google sign-in window and Supabase Auth.

Features
- Google OAuth PKCE sign-in through the system browser.
- Opens https://huevo.su/clicker, allows manual Huevo sign-in, selection of a page control, and start/stop clicking.
- Shows click totals, session count, speed, elapsed time, and logs.
- Stores user profiles and click session statistics in Supabase with per-user row-level security.
- Limits: 5 clicks/second and 10,000 clicks/session.

Statistics count successful browser click actions; the app cannot guarantee the website credited every action. Use automation only if permitted by the site's rules. The app does not bypass CAPTCHA or anti-bot protections.

One-time Supabase / Google OAuth setup
--------------------------------------
Supabase project: https://supabase.com/dashboard/project/hzcexklqkpgkdbpzdhfx

1. In Supabase Dashboard, open Authentication -> Sign In / Providers -> Google and enable Google.
2. In Google Cloud Console (https://console.cloud.google.com/), configure the OAuth consent screen and create an OAuth client ID of type Web application.
3. In Google OAuth Authorized redirect URIs, add exactly:
   https://hzcexklqkpgkdbpzdhfx.supabase.co/auth/v1/callback
4. Copy the Google client ID and client secret into the Supabase Google provider settings and save.
5. In Supabase Authentication -> URL Configuration -> Redirect URLs, add exactly:
   http://127.0.0.1:8765/callback
6. Google OAuth will not work until the provider credentials and redirect allowlist are configured.

Never put the Google client secret or a Supabase service-role key in the app or repository. The app uses only a publishable key and the signed-in user's access token.

Run from source (Windows 10/11, Python 3.10+)
---------------------------------------------
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python main.py

Use
---
1. Launch HuevoHelper and click Продолжить с Google.
2. Finish Google sign-in in the browser; the app returns to the main window.
3. Open the browser, sign in to Huevo manually if needed, select the intended clicker element.
4. Click Старт автокликера, then Стоп. Session statistics are sent to Supabase when the session ends.

Build
-----
Run build.bat or download the HuevoHelper-Windows artifact from GitHub Actions. Chromium must be installed separately on the computer running the app: python -m playwright install chromium.
