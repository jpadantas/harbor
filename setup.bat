@echo off
REM ==========================================================
REM  HARBOR -- Setup Script
REM  Creates a Python virtual environment and installs all
REM  dependencies listed in requirements.txt.
REM ==========================================================

echo.
echo ==================================================
echo  HARBOR -- Environment Setup
echo ==================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

REM Create virtual environment if it does not exist
if exist .venv\Scripts\python.exe (
    echo [1/3] Virtual environment already exists -- skipping creation.
) else (
    echo [1/3] Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Done.
)

REM Activate environment
echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install requirements
echo [3/3] Installing dependencies from requirements.txt...
pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo  Setup complete!
echo  To activate the environment manually, run:
echo    .venv\Scripts\activate
echo ==================================================
echo.
pause
