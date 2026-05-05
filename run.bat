@echo off
REM ==========================================================
REM  HARBOR -- Run Script
REM  1. Calibrates movement priors from the AIS dataset
REM  2. Runs the HARBOR pipeline on all SAR images in data\
REM ==========================================================

echo.
echo ==================================================
echo  HARBOR -- Run Pipeline
echo ==================================================
echo.

REM Resolve the venv Python executable explicitly
set PYTHON=.venv\Scripts\python.exe

if not exist %PYTHON% (
    echo [ERROR] Virtual environment not found.
    echo         Please run setup.bat first.
    pause
    exit /b 1
)

REM -------------------------------------------------------
REM  Step 1 -- AIS Calibration
REM -------------------------------------------------------
set AIS_INPUT=data\AIS_Dataset.xlsx
set CALIBRATION_OUT=data\ais_calibration.json
set CALIBRATION_FLAG=

if not exist %AIS_INPUT% goto skip_calibration

echo [1/2] Running AIS calibration...
%PYTHON% src\calibrate_from_ais.py --input %AIS_INPUT% --output %CALIBRATION_OUT%
if errorlevel 1 (
    echo [WARNING] Calibration failed -- HARBOR will use hardcoded defaults.
    goto run_harbor
)
echo       Calibration complete: %CALIBRATION_OUT%
set CALIBRATION_FLAG=--calibration %CALIBRATION_OUT%
goto run_harbor

:skip_calibration
echo [1/2] AIS dataset not found (%AIS_INPUT%) -- skipping calibration.
echo       HARBOR will use hardcoded movement priors.

:run_harbor
echo.

REM -------------------------------------------------------
REM  Step 2 -- Run HARBOR on all .tif files in data\
REM -------------------------------------------------------
echo [2/2] Scanning data\ for SAR images (*.tif)...

set FOUND=0
for %%F in (data\*.tif) do (
    set FOUND=1
    echo.
    echo       Processing: %%F
    %PYTHON% src\harbor.py --input "%%F" --output-dir outputs --threshold 0.99 --future-minutes 360 %CALIBRATION_FLAG%
    if errorlevel 1 echo [WARNING] harbor.py returned an error for %%F
)

if %FOUND%==0 (
    echo.
    echo [WARNING] No .tif files found in data\.
    echo           Place a SAR GeoTIFF image in data\ and re-run.
)

echo.
echo ==================================================
echo  HARBOR pipeline finished. Results saved to: outputs\
echo ==================================================
echo.
pause
