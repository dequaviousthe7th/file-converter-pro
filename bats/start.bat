@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo    File Converter Pro v1.0.0
echo ==========================================
echo.

REM Go to parent directory (project root)
cd /d "%~dp0.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
echo.
    pause
    exit /b 1
)

echo Found:
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Checking dependencies...
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo Installing dependencies (first time only)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo WARNING: Some dependencies may have failed, trying to continue...
    )
)

echo.
echo Starting File Converter Pro...
echo.

REM Run the desktop application
python app.py

if errorlevel 1 (
    echo.
    echo Application stopped.
    pause
)
