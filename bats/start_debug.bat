@echo off
echo ==========================================
echo    File Converter Pro - DEBUG MODE
echo ==========================================
echo.

cd /d "%~dp0.."

echo Current directory: %CD%
echo.

python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting application...
python app.py

pause
