@echo off
REM Quick test to verify naive config underperforms
REM Run as administrator

echo ============================================================
echo TESTING BOTH CONFIGS TO VERIFY NAIVE UNDERPERFORMS
echo ============================================================

set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
call C:\Users\Yugen\gdrive\workspace\.venv\Scripts\activate.bat
cd /d "%~dp0"

echo.
echo [1/2] Testing ADAPTIVE (good) configuration...
echo ============================================================
python traffic_controller_configurable.py configs\adaptive_config.json

echo.
echo.
echo [2/2] Testing NAIVE (poor) configuration...
echo ============================================================
python traffic_controller_configurable.py configs\naive_config.json

echo.
echo.
echo ============================================================
echo TESTS COMPLETE
echo ============================================================
echo.
echo Check the output above to compare:
echo   - Average waiting time (should be higher for naive)
echo   - Average queue length (should be higher for naive)
echo   - Objective value (should be higher for naive = worse)
echo.
echo Full logs saved in logs/ directory with timestamps
echo.
pause
