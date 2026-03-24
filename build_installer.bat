@echo off
echo Building ExileHUD-Setup.exe ...

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller --quiet
)

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "ExileHUD-Setup" ^
    --icon "assets\icon.ico" ^
    installer_gui.py

echo.
if exist "dist\ExileHUD-Setup.exe" (
    echo SUCCESS: dist\ExileHUD-Setup.exe is ready to share.
) else (
    echo FAILED: check the output above for errors.
)
pause
