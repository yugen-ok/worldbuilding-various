@echo off
REM Run this batch file as Administrator
REM Right-click -> "Run as administrator"

echo Setting up environment...
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

echo Activating virtual environment...
call C:\Users\Yugen\gdrive\workspace\.venv\Scripts\activate.bat

echo Running traffic controller...
cd /d "%~dp0"
python traffic_controller.py

echo.
echo Simulation complete!
pause
