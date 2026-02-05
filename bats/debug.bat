@echo off
echo ==========================================
echo    File Converter Pro - DEBUG
echo ==========================================
echo.

cd /d "%~dp0.."
call venv\Scripts\activate

echo Running with error output...
echo.
python app.py 2>&1

echo.
echo Exit code: %errorlevel%
echo.
pause
