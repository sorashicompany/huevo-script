# HuevoHelper

Windows desktop helper for the Huevo clicker page. Built with Python, Tkinter, and Playwright.

## What it does
- Opens `https://huevo.su/clicker` in a separate Chromium window.
- You sign in yourself in the browser; the app does not ask for or store credentials.
- Scans visible page controls and lets you select the intended piggy-bank/cat element.
- Provides a single-click button and a start/stop autoclicker.
- Shows successful click totals, session count, average rate, elapsed time, and timestamped logs.
- Safety limits: up to 5 clicks per second and 10,000 clicks per session. The app does not attempt to bypass CAPTCHA, anti-bot controls, or site restrictions.

Use automated clicking only if the site's rules allow it. The app cannot guarantee that a click was credited by the service; its statistics count successful browser click actions.

## Run from source
Windows 10/11 and Python 3.10+:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## Use
1. Launch HuevoHelper.
2. Click **Открыть браузер**. The clicker page opens.
3. Sign in manually if needed.
4. Click **Обновить элементы**.
5. Select the row corresponding to the piggy-bank/cat on the page.
6. Click **Старт автокликера** and confirm. Click **Стоп** to stop at any time.

If the page uses an unlabeled canvas rather than a button, it may not appear in the element list; this version intentionally does not guess coordinates.

## Build
Run `build.bat`, or download the Windows executable from the latest successful GitHub Actions run's `HuevoHelper-Windows` artifact. Chromium must be installed separately on the computer running the app:
```powershell
py -m playwright install chromium
```

The GitHub Actions workflow builds `dist/HuevoHelper.exe` and publishes it as an artifact for 14 days.
