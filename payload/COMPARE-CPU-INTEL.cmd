@echo off
cd /d "%~dp0"
title ShortsFlow - CPU versus Intel
echo Keep other video processing stopped during this comparison.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0COMPARE-CPU-INTEL.ps1"
echo.
echo Report: CPU-INTEL-COMPARISON.json
pause
