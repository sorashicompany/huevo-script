@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error
set "PLAYWRIGHT_BROWSERS_PATH=%CD%\playwright-browsers"
py -m playwright install chromium
if errorlevel 1 goto :error
pyinstaller --noconfirm --clean --onefile --windowed --name HuevoHelper main.py
if errorlevel 1 goto :error
xcopy /E /I /Y "playwright-browsers" "dist\playwright-browsers" >nul
if errorlevel 1 goto :error
echo.
echo Build complete: dist\HuevoHelper.exe
echo Keep dist\playwright-browsers beside HuevoHelper.exe.
pause
exit /b 0
:error
echo.
echo Build failed. Check the error output above.
pause
exit /b 1
