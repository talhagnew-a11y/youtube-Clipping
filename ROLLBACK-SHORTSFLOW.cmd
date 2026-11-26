@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Rollback-ShortsFlow.ps1"
if errorlevel 1 echo Rollback did not finish. Read the message above.
pause
