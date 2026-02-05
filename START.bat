@echo off
REM Main launcher - redirects to bats directory
cd /d "%~dp0"
call bats\start.bat
