@echo off
cd /d "%~dp0"
call venv\Scripts\activate

REM Check if dependencies are installed
python -c "import reportlab" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

python app_simple.py
if errorlevel 1 pause
