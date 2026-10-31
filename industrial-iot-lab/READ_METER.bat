@echo off
rem I run the reader with the same environment as the server.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" read_meter.py --cycles 2
set "lab_result=%errorlevel%"
echo.
echo Reader finished with exit code %lab_result%. Zero means success.
pause
exit /b %lab_result%
:missing
echo Run SETUP.bat first.
pause
exit /b 1
