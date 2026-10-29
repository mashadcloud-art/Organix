@echo off
cd /d "%~dp0"
echo ========================================================
echo  Pushing Organix to https://github.com/mashadcloud-art/Organix
echo ========================================================
git push -u origin main
echo.
echo Push completed!
pause
