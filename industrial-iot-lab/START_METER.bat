@echo off
rem I use the project's Python so installed packages are available.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
echo Leave this window open while reading the meter. Stop with Ctrl+C.
".venv\Scripts\python.exe" meter_simulator.py
set "lab_result=%errorlevel%"
echo Simulator stopped with exit code %lab_result%.
pause
exit /b %lab_result%
:missing
echo Run SETUP.bat first.
pause
exit /b 1
