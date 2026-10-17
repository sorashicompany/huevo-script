Huevo tools
===========

Three independent Windows apps:
- **HuevoClicker.exe** — clicker for https://huevo.su/clicker
- **HuevoBottle.exe** — auto-buttons for the bottle game at https://huevo.su/apps/
- **HuevoCasino.exe** — helper for the «Шарик» game at https://huevo.su/apps/1

All apps use installed Google Chrome and Playwright's local DevTools connection. Browser profiles are separate under %LOCALAPPDATA%\HuevoHelper\ (browser-profile, bottle-profile, and casino-profile), so you may need to sign in separately.

## Run from source (Windows 10/11, Python 3.10+)

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python main.py
    python bottle.py
    python casino.py

## Build

Run build.bat to create all three executables in dist/.

GitHub Actions publishes three separate artifacts:
- **HuevoClicker-Windows** — HuevoClicker.exe
- **HuevoBottle-Windows** — HuevoBottle.exe
- **HuevoCasino-Windows** — HuevoCasino.exe

Download them from the latest successful workflow run in Actions. Google Chrome must be installed. Casino automation treats the visible «БАХ!» label as a loss and assumes four pumps without that label indicate a win. Check the game behavior carefully and use only if permitted by the site's rules. Doubling after repeated losses can rapidly increase the amount wagered; stop the bot if the stake or game state does not match expectations.
