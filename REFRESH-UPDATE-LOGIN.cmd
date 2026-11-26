@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-ShortsFlow.ps1" -RefreshLogin
pause
