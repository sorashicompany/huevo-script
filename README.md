Huevo tools
===========

Two independent Windows apps:
- **HuevoClicker.exe** — clicker for https://huevo.su/clicker
- **HuevoBottle.exe** — auto-buttons for the bottle game at https://huevo.su/apps/

Both use installed Google Chrome and Playwright's local DevTools connection. Browser profiles are separate under `%LOCALAPPDATA%\HuevoHelper\` (`browser-profile` and `bottle-profile`), so you may need to sign in separately.

## Run from source (Windows 10/11, Python 3.10+)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
# Run separately for the bottle app:
python bottle.py
```

## Build

Run `build.bat` to create both executables in `dist\`.

GitHub Actions publishes two separate artifacts:
- **HuevoClicker-Windows** — `HuevoClicker.exe`
- **HuevoBottle-Windows** — `HuevoBottle.exe`

Download both from the latest successful workflow run in Actions. Google Chrome must be installed. Automation only clicks visible, enabled game buttons and does not bypass CAPTCHA or other anti-bot protections. Use automation only if permitted by the site's rules.
