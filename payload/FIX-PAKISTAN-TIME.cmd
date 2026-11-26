@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Sync-Pakistan-Time.ps1" -RequestAdmin
