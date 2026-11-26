param([string]$ReportName='GPU-TEST-RESULTS')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$pyDir=Get-ChildItem -LiteralPath (Join-Path $root 'python') -Directory |
 Where-Object {$_.Name -match '^cpython-3\.12\.' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'python.exe'))} |
 Select-Object -First 1
if(-not $pyDir){throw 'Copy the complete shortsflow folder first. Bundled Python is missing.'}
New-Item -ItemType Directory -Force -Path (Join-Path $root 'temp') | Out-Null
$env:PYTHONUTF8='1'
$env:PYTHONUNBUFFERED='1'
& (Join-Path $pyDir.FullName 'python.exe') (Join-Path $root 'tools/gpu-test.py') $ReportName
exit $LASTEXITCODE
