@echo off
REM Build the FCP-Setup.exe installer using Inno Setup
REM Run this from the installer\ directory

setlocal

set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC%" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if not exist "%ISCC%" (
    echo ERROR: Inno Setup not found.
    echo Install it from: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo Building File Converter Pro installer...
echo.

"%ISCC%" setup.iss

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   BUILD SUCCESSFUL!
    echo   Output: ..\dist\FCP-Setup.exe
    echo ============================================
) else (
    echo.
    echo   BUILD FAILED. Check the output above.
)

pause
