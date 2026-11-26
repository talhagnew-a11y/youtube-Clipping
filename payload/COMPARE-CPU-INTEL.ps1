$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$pyDir=Get-ChildItem -LiteralPath (Join-Path $root 'python') -Directory |
 Where-Object { $_.Name -match '^cpython-3\.12\.' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'python.exe')) } |
 Select-Object -First 1
if(-not $pyDir){throw 'Bundled Python missing. Use the complete shortsflow folder.'}
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
$env:PYTHONPATH=Join-Path $root 'venv/Lib/site-packages'
& (Join-Path $pyDir.FullName 'python.exe') (Join-Path $root 'tools/compare-cpu-intel.py')
exit $LASTEXITCODE
