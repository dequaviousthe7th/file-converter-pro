@echo off
REM Post-installation setup for File Converter Pro
REM Creates virtual environment and installs Python packages

setlocal

set "APP_DIR=%~1"
if "%APP_DIR%"=="" set "APP_DIR=%~dp0.."

echo.
echo ============================================
echo   File Converter Pro - Setting Up...
echo ============================================
echo.

cd /d "%APP_DIR%"

REM Find Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check Python version
python --version 2>&1 | findstr /r "3\.[8-9]\. 3\.1[0-9]\." >nul
if %errorlevel% neq 0 (
    echo WARNING: Python 3.8+ recommended.
    echo Current version:
    python --version
    echo.
)

REM Create virtual environment
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate and install packages
echo.
echo Installing packages (this may take a few minutes)...
call venv\Scripts\activate

python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some packages may have failed to install.
    echo The app may still work for most conversions.
) else (
    echo All packages installed successfully.
)

REM Create output directory
if not exist "converted" mkdir converted

echo.
echo ============================================
echo   Setup complete! You can now use the app.
echo ============================================
echo.

exit /b 0
