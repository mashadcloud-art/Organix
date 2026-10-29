@echo off
cd /d "%~dp0"
echo ========================================================
echo  Building Organix Standalone EXE...
echo ========================================================
python -m PyInstaller --noconsole --onefile --name "Organix" --icon "app_icon.ico" --add-data "web;web" --add-data "rules.json;." file_organizer.py
echo.
echo Build complete! Your portable executable is ready in:
echo %~dp0dist\Organix.exe
echo.
pause
