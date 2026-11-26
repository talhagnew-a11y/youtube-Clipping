@echo off
cd /d "%~dp0"
title ShortsFlow - Small GPU Test
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TEST-GPU.ps1"
echo.
echo Send GPU-TEST-RESULTS.json from this folder to your assistant.
pause
