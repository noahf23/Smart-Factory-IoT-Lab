@echo off
rem I run the reproducible checks with an isolated server and temporary database.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" verify_lab.py
set "lab_result=%errorlevel%"
echo Verification exit code: %lab_result%.
pause
exit /b %lab_result%
:missing
echo Run SETUP.bat first.
pause
exit /b 1
