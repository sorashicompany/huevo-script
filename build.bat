@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto :error
py -m pip install -r requirements.txt
if errorlevel 1 goto :error
pyinstaller --noconfirm --clean --onefile --windowed --name HuevoClicker main.py
if errorlevel 1 goto :error
pyinstaller --noconfirm --clean --onefile --windowed --name HuevoBottle bottle.py
if errorlevel 1 goto :error
pyinstaller --noconfirm --clean --onefile --windowed --name HuevoCasino casino.py
if errorlevel 1 goto :error
echo.
echo Build complete:
echo dist\HuevoClicker.exe
echo dist\HuevoBottle.exe
echo dist\HuevoCasino.exe
pause
exit /b 0
:error
echo.
echo Build failed. Check the error output above.
pause
exit /b 1
