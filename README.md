HuevoHelper
===========

Windows desktop clicker helper. No Google sign-in or cloud account is required.

Features
- Opens https://huevo.su/clicker, allows manual Huevo sign-in, selection of a page control, and start/stop clicking.
- Shows click totals, session count, speed, elapsed time, and logs.
- Opens the installed Google Chrome as a separate browser process and connects to it through its local DevTools endpoint. The login profile is persistent.
- Shows click statistics locally; cloud statistics are disabled.
- Limits: 5 clicks/second and 10,000 clicks/session.

Statistics count successful browser click actions; the app cannot guarantee the website credited every action. Use automation only if permitted by the site's rules. The app does not bypass CAPTCHA or anti-bot protections.

Run from source (Windows 10/11, Python 3.10+)
---------------------------------------------
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python main.py

Use
---
1. Launch HuevoHelper; no account sign-in is required.
2. Open the browser and sign in to Huevo manually if needed. The browser profile is stored under `%LOCALAPPDATA%\\HuevoHelper\\browser-profile`.
3. Select the intended clicker element.
4. Click Старт автокликера, then Стоп. Statistics are displayed locally; they are not synced to the cloud.

Build
-----
Run build.bat or download the HuevoHelper-Windows artifact from GitHub Actions. The GitHub Actions artifact contains only `HuevoHelper.exe`. The app uses Google Chrome installed on Windows and attaches to its separately launched window through a local DevTools endpoint, so no browser bundle is needed. If Chrome is missing, install Google Chrome and launch the app again.
