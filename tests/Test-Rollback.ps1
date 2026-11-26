param([string]$PackageRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$base=Join-Path ([IO.Path]::GetTempPath()) ('shortsflow-rollback-test-'+[Guid]::NewGuid().ToString('N'))
$install=Join-Path $base 'installed'
$package=Join-Path $base 'package'
New-Item -ItemType Directory -Force -Path (Join-Path $install 'venv/Lib/site-packages/shortsflow'),(Join-Path $install 'workspace'),$package | Out-Null
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/__init__.py') -Value '__version__ = "0.9.4"'
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/webui.py') -Value 'old layout'
Set-Content -LiteralPath (Join-Path $install 'workspace/schedule.json') -Value '[{"status":"pending"}]'
Set-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Value 'test sign-in'
Set-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Value '{"version":"previous.test"}'
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Apply-ShortsFlow-Update.ps1') -Destination $install
Set-Content -LiteralPath (Join-Path $package 'webui.py') -Value 'new layout'
$file=Get-Item -LiteralPath (Join-Path $package 'webui.py')
@{schema=1;version='new.test';upstream_version='0.9.4';files=@(@{source='webui.py';target='venv/Lib/site-packages/shortsflow/webui.py';bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash})} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $package 'update-manifest.json')
& (Join-Path $PackageRoot 'Apply-ShortsFlow-Update.ps1') -InstallRoot $install -PackageRoot $package -NoRestart
& (Join-Path $PackageRoot 'Rollback-ShortsFlow.ps1') -InstallRoot $install -NoRestart
if((Get-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/webui.py') -Raw).Trim() -ne 'old layout'){throw 'Old layout was not restored.'}
if((Get-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Raw).Trim() -ne 'test sign-in'){throw 'Sign-in changed.'}
if((Get-Content -LiteralPath (Join-Path $install 'workspace/schedule.json') -Raw).Trim() -ne '[{"status":"pending"}]'){throw 'Schedule changed.'}
if((Get-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Raw | ConvertFrom-Json).version -ne 'previous.test'){throw 'Version was not restored.'}
$rejected=$false
try{& (Join-Path $PackageRoot 'Rollback-ShortsFlow.ps1') -InstallRoot $install -BackupPath $base -NoRestart}catch{$rejected=$true}
if(-not $rejected){throw 'Backup outside intended root was accepted.'}
Write-Output 'PASS: previous layout and version restored; pending schedules and sign-in preserved; outside backup rejected.'
