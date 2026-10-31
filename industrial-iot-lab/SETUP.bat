@echo off
rem I work from the extracted project folder, including paths with spaces.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
rem I try the Python launcher first, then the python command.
py -3 -m venv .venv
if not errorlevel 1 goto install
python -m venv .venv
if errorlevel 1 goto failed
:install
rem I install only from the bundled package, without accessing the internet.
".venv\Scripts\python.exe" -m pip install --no-index --find-links="packages" -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "from pymodbus.server import StartTcpServer; from pymodbus.simulator import SimDevice; from pymodbus.client import ModbusTcpClient; import pymodbus; print('Installed PyModbus', pymodbus.__version__)"
if errorlevel 1 goto failed
echo.
echo Setup complete. Open START_METER.bat, then READ_METER.bat.
pause
exit /b 0
:failed
echo.
echo Setup failed. Python 3.10 or newer must be installed.
echo Keep this window open and share the error above for troubleshooting.
pause
exit /b 1
