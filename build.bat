@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error
pyinstaller --noconfirm --clean --onefile --windowed --name HuevoHelper main.py
if errorlevel 1 goto :error
echo.
echo Build complete: dist\HuevoHelper.exe
echo Playwright Chromium must be installed separately:
echo   py -m playwright install chromium
pause
exit /b 0
:error
echo.
echo Build failed. Check the error output above.
pause
exit /b 1
