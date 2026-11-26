@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; $p=New-Object System.Windows.Forms.OpenFileDialog; $p.Filter='GitHub update ZIP (*.zip)|*.zip'; if($p.ShowDialog() -eq 'OK'){ & (Join-Path (Get-Location) 'Update-ShortsFlow.ps1') -PackageZip $p.FileName }"
echo.
pause
