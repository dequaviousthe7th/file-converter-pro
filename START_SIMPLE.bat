@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python app_simple.py
if errorlevel 1 pause
