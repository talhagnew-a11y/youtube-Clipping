@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-Portable.ps1"
set "SHORTSFLOW_FAST_MODE=0"
call "%~dp0RUN-SHORTSFLOW.cmd"
