@echo off
echo ==========================================
echo  File Converter Pro - Shortcut Creator
echo ==========================================
echo.

cd /d "%~dp0.."
set "APP_DIR=%CD%"

REM Get Desktop path
for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop') do set "DESKTOP=%%b"
set "DESKTOP=%DESKTOP:%%USERPROFILE%%=%USERPROFILE%"

echo Creating shortcut on your Desktop...
echo Desktop: %DESKTOP%
echo.

REM Create VBScript to make shortcut
set "VBSFILE=%TEMP%\create_shortcut.vbs"
(
echo Set WshShell = WScript.CreateObject("WScript.Shell"^)
echo Set Shortcut = WshShell.CreateShortcut("%DESKTOP%\File Converter Pro.lnk"^)
echo Shortcut.TargetPath = "%APP_DIR%\START.bat"
echo Shortcut.WorkingDirectory = "%APP_DIR%"
echo Shortcut.IconLocation = "shell32.dll,14"
echo Shortcut.Description = "File Converter Pro - Convert PDF, Word, Images & more"
echo Shortcut.Save
) > "%VBSFILE%"

cscript //nologo "%VBSFILE%"
del "%VBSFILE%"

echo.
echo Shortcut created!
pause
