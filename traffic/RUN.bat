@echo off
REM Run traffic controller with config selection
REM Right-click -> "Run as administrator"

echo ============================================================
echo TRAFFIC CONTROLLER - CONFIG SELECTOR
echo ============================================================
echo.
echo Available configurations:
echo   1. Adaptive (Optimized) - Default
echo   2. Naive (Fixed-time, poor parameters)
echo   3. Both (run comparison)
echo.

choice /C 123 /N /M "Select configuration [1-3, default=1]: " /T 5 /D 1

if errorlevel 3 goto BOTH
if errorlevel 2 goto NAIVE
if errorlevel 1 goto ADAPTIVE

:ADAPTIVE
echo.
echo ============================================================
echo Running ADAPTIVE configuration...
echo ============================================================
set CONFIG=configs\adaptive_config.json
goto RUN_SINGLE

:NAIVE
echo.
echo ============================================================
echo Running NAIVE configuration...
echo ============================================================
set CONFIG=configs\naive_config.json
goto RUN_SINGLE

:RUN_SINGLE
echo.
echo Setting up environment...
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

echo Activating virtual environment...
call C:\Users\Yugen\gdrive\workspace\.venv\Scripts\activate.bat

echo.
echo Starting simulation with config: %CONFIG%
cd /d "%~dp0"
python controller.py %CONFIG%

echo.
echo ============================================================
echo Simulation complete!
echo Check the logs/ directory for results.
echo ============================================================
pause
exit /b

:BOTH
echo.
echo ============================================================
echo Running BOTH configurations for comparison...
echo ============================================================
echo.

set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
call C:\Users\Yugen\gdrive\workspace\.venv\Scripts\activate.bat
cd /d "%~dp0"

echo.
echo [1/2] Running ADAPTIVE configuration...
echo --------------------------------------------------------
python controller.py configs\adaptive_config.json > temp_adaptive.txt
type temp_adaptive.txt | findstr /C:"Objective value"
set ADAPTIVE_OBJ=
for /f "tokens=3" %%a in ('type temp_adaptive.txt ^| findstr /C:"Objective value"') do set ADAPTIVE_OBJ=%%a

echo.
echo [2/2] Running NAIVE configuration...
echo --------------------------------------------------------
python controller.py configs\naive_config.json > temp_naive.txt
type temp_naive.txt | findstr /C:"Objective value"
set NAIVE_OBJ=
for /f "tokens=3" %%a in ('type temp_naive.txt ^| findstr /C:"Objective value"') do set NAIVE_OBJ=%%a

echo.
echo ============================================================
echo COMPARISON RESULTS
echo ============================================================
echo.
echo Adaptive Config:
type temp_adaptive.txt | findstr /C:"Average waiting time" /C:"Average queue" /C:"Objective value"
echo.
echo Naive Config:
type temp_naive.txt | findstr /C:"Average waiting time" /C:"Average queue" /C:"Objective value"
echo.
echo ============================================================
echo CONCLUSION: Lower objective value is better
echo ============================================================
echo.
echo Full logs saved to logs/ directory
echo.

del temp_adaptive.txt
del temp_naive.txt

pause
exit /b
