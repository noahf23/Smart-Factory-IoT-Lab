@echo off
rem I use a menu to apply controlled faults to the simulated devices.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
:menu
echo.
echo 1. Freeze meter 3 source data
echo 2. Make meter 2 unavailable
echo 3. Restore all meters
echo 4. Exit
choice /c 1234 /n /m "Choose 1-4: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto restore
if errorlevel 2 goto offline
".venv\Scripts\python.exe" fault_control.py 3 freeze
goto menu
:offline
".venv\Scripts\python.exe" fault_control.py 2 offline
goto menu
:restore
".venv\Scripts\python.exe" fault_control.py all normal
goto menu
:missing
echo Run SETUP.bat first.
pause
exit /b 1
