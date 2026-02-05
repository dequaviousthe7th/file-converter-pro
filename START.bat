@echo off
cd /d "%~dp0"
call venv\Scripts\activate

REM Check if customtkinter is installed
python -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo Installing customtkinter...
    pip install customtkinter pillow
)

python app.py
if errorlevel 1 pause
