@echo off
cd /d "%~dp0"
echo ========================================================
echo  Building Organix Standalone & Setup Wizard...
echo ========================================================
echo 1. Compiling Organix.exe...
python -m PyInstaller --noconsole --onefile --name "Organix" --icon "app_icon.ico" --add-data "web;web" --add-data "rules.json;." file_organizer.py

echo 2. Compiling Organix_Setup.exe...
python -m PyInstaller --noconsole --onefile --name "Organix_Setup" --icon "app_icon.ico" --add-data "dist\Organix.exe;." --add-data "app_icon.ico;." installer_wizard.py

echo.
echo ========================================================
echo  Builds Complete!
echo  Portable App: %~dp0dist\Organix.exe
echo  Setup Wizard: %~dp0dist\Organix_Setup.exe
echo ========================================================
pause
