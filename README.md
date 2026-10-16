# Huevo Desktop Helper

A small Windows desktop helper built from scratch with Python, Tkinter, and Playwright. The repository previously had no source files, so this is a clean starter implementation rather than a recreation of an unavailable original script.

## Features
- Open a website in a separate Chromium window.
- Inspect visible buttons, links, and form fields.
- Select an element and optionally click it after a confirmation prompt.
- No password capture, credential storage, or hidden background actions.

## Requirements
- Windows 10/11
- Python 3.10+
- Internet access for the first Playwright browser installation

## Run from source
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## Build a Windows executable
Run `build.bat`. The executable will be placed in `dist\HuevoHelper.exe`.

Playwright's Chromium browser is installed separately from the executable. On first launch, if Chromium is missing, the app will explain how to install it.

## Notes
This is a generic website helper because the linked repository was empty and did not include an original script or feature specification. Use it only on websites you are authorized to access, and follow the site's rules.
