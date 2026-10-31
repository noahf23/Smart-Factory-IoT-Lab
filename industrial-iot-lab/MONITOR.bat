@echo off
rem I poll continuously using the project environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" read_meter.py --watch
set "lab_result=%errorlevel%"
echo Monitoring stopped. Exit code: %lab_result%.
pause
exit /b %lab_result%
:missing
echo Run SETUP.bat first.
pause
exit /b 1
