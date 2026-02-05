@echo off
echo ==========================================
echo    Fixing Dependencies
echo ==========================================
echo.

cd /d "%~dp0.."
call venv\Scripts\activate

echo Updating pip...
python -m pip install --upgrade pip

echo.
echo Installing pdf2docx and dependencies...
pip install pdf2docx==0.5.8
pip install PyMuPDF
pip install python-docx
pip install pypdf
pip install reportlab
pip install pillow

echo.
echo Testing import...
python -c "from pdf2docx import Converter; print('pdf2docx OK')"

echo.
echo ==========================================
echo Done! Press any key to exit.
echo ==========================================
pause
