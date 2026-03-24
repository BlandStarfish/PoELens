@echo off
echo ============================================
echo   PoELens Installer Builder
echo ============================================
echo.

:: Inject current password hash from installer_password.json into installer_gui.py
python inject_password.py
if errorlevel 1 (
    echo [ERROR] Password injection failed. Run set_password.py first.
    pause & exit /b 1
)

:: Check / install PyInstaller
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller --quiet
)

:: Build
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "PoELens-Setup" ^
    --icon "assets\icon.ico" ^
    installer_gui.py

echo.
if exist "dist\PoELens-Setup.exe" (
    :: Zip it
    python -c "import zipfile,os; z=zipfile.ZipFile('PoELens-Setup.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9); z.write('dist/PoELens-Setup.exe','PoELens-Setup.exe'); z.close(); print(f'ZIP: {os.path.getsize(chr(34)+\"PoELens-Setup.zip\"+chr(34))/1024/1024:.1f} MB')"
    echo.
    echo SUCCESS: PoELens-Setup.zip is ready to share.
) else (
    echo FAILED: check output above for errors.
)
pause
