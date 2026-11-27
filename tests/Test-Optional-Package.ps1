param([string]$RepositoryRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$base=Join-Path ([IO.Path]::GetTempPath()) ('shortsflow-optional-package-test-'+[Guid]::NewGuid().ToString('N'))
$install=Join-Path $base 'installed'
$package=Join-Path $base 'package'
New-Item -ItemType Directory -Force -Path $install,$package,(Join-Path $install 'workspace'),(Join-Path $install 'models') | Out-Null
$source=Join-Path $RepositoryRoot 'improvements'
Copy-Item -Path (Join-Path $source '*') -Destination $package -Recurse
$manifest=Get-Content -LiteralPath (Join-Path $package 'improvement-manifest.json') -Raw | ConvertFrom-Json
$stableVersion=$manifest.required_base
$initialOptionalVersion=$manifest.version
$v=[version]$initialOptionalVersion
$laterOptionalVersion=('{0}.{1}.{2}.{3}' -f $v.Major,$v.Minor,$v.Build,($v.Revision+1))
$hashes=@{}
foreach($file in $manifest.base_files){
 $target=Join-Path $install $file.path
 New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
 Copy-Item -LiteralPath (Join-Path (Join-Path $RepositoryRoot 'payload') $file.path) -Destination $target
 $hashes[$file.path]=(Get-FileHash -LiteralPath $target).Hash
}
Set-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Value ('{"version":"'+$stableVersion+'"}')
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/__init__.py') -Value '__version__ = "0.9.4"'
Set-Content -LiteralPath (Join-Path $install 'workspace/schedule.json') -Value '[{"id":"saved-job","status":"pending","at":"2026-12-01 09:00"}]'
Set-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Value 'login sentinel'
Set-Content -LiteralPath (Join-Path $install 'models/model.bin') -Value 'model sentinel'
$apply=Join-Path $source 'Apply-Improvements.ps1'
function Assert($Condition,$Message){if(-not $Condition){throw $Message}}
function VerifyStable {
 foreach($path in $hashes.Keys){Assert ((Get-FileHash -LiteralPath (Join-Path $install $path)).Hash -eq $hashes[$path]) ('Stable code changed: '+$path)}
 Assert ((Get-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Raw | ConvertFrom-Json).version -eq $stableVersion) 'Normal update version changed.'
 Assert ((Get-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Raw).Trim() -eq 'login sentinel') 'Login changed.'
 Assert ((Get-Content -LiteralPath (Join-Path $install 'models/model.bin') -Raw).Trim() -eq 'model sentinel') 'Model changed.'
 Assert ((Get-Content -LiteralPath (Join-Path $install 'workspace/schedule.json') -Raw | ConvertFrom-Json)[0].id -eq 'saved-job') 'Schedule changed.'
}
& $apply -InstallRoot $install -PackageRoot $package -CheckOnly
Assert (-not(Test-Path -LiteralPath (Join-Path $install 'improvements/state/installed.json'))) 'CheckOnly installed optional code.'
$archive=Join-Path $base 'optional.zip'
Compress-Archive -Path $package -DestinationPath $archive
& (Join-Path $source 'Update-Improvements.ps1') -InstallRoot $install -PackageZip $archive -CheckOnly
Assert (-not(Test-Path -LiteralPath (Join-Path $install 'improvements/state/installed.json'))) 'ZIP CheckOnly installed optional code.'
Set-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Value '{"version":"2026.11.26.7"}'
$rejected=$false
try{& $apply -InstallRoot $install -PackageRoot $package -CheckOnly}catch{$rejected=$true}
Assert $rejected 'Old stable base was accepted.'
Set-Content -LiteralPath (Join-Path $install 'UPDATE-VERSION.json') -Value ('{"version":"'+$stableVersion+'"}')
function Get-CimInstance {param($ClassName,$Filter) return [pscustomobject]@{ExecutablePath=(Join-Path $install 'python/python.exe');CommandLine='python -m shortsflow_improvements.bootstrap';ProcessId=123}}
$rejected=$false
try{& $apply -InstallRoot $install -PackageRoot $package}catch{$rejected=$true}
Remove-Item Function:\Get-CimInstance
Assert $rejected 'Active test app did not block optional installation.'
& $apply -InstallRoot $install -PackageRoot $package
$installed=Join-Path $install 'improvements'
$marker=Join-Path $installed 'state/installed.json'
Assert ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).enabled) 'Optional code was not enabled for explicit test launch.'
Assert ((Get-Content -LiteralPath (Join-Path $installed 'state/queue.json') -Raw | ConvertFrom-Json).paused) 'First test install did not start with its automatic queue paused.'
& (Join-Path $installed 'Launch-Improvements.ps1') -CheckOnly
VerifyStable
& (Join-Path $installed 'Rollback-Improvements.ps1')
Assert (-not (Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).enabled) 'First rollback did not disable optional mode.'
VerifyStable
# Install v1 again, then a changed v2, and verify v2 rollback restores v1 code.
& $apply -InstallRoot $install -PackageRoot $package
$runtime=Join-Path $package 'runtime/shortsflow_improvements/__init__.py'
$original=Get-Content -LiteralPath $runtime -Raw
Add-Content -LiteralPath $runtime -Value '# simulated optional revision 2'
$manifest.version=$laterOptionalVersion
foreach($entry in $manifest.files){if($entry.path -eq 'runtime/shortsflow_improvements/__init__.py'){$entry.bytes=(Get-Item -LiteralPath $runtime).Length;$entry.sha256=(Get-FileHash -LiteralPath $runtime).Hash}}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $package 'improvement-manifest.json')
$lock=[IO.File]::Open((Join-Path $installed 'runtime/shortsflow_improvements/__init__.py'),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
$rejected=$false
try{try{& $apply -InstallRoot $install -PackageRoot $package}catch{$rejected=$true}}finally{$lock.Dispose()}
Assert $rejected 'Locked optional file did not reject installation.'
Assert ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).version -eq $initialOptionalVersion) 'Failed optional update changed its version.'
VerifyStable
& $apply -InstallRoot $install -PackageRoot $package
Assert ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).version -eq $laterOptionalVersion) 'Optional v2 missing.'
& (Join-Path $installed 'Rollback-Improvements.ps1')
Assert ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).version -eq $initialOptionalVersion) 'Previous optional version not restored.'
Assert ((Get-Content -LiteralPath (Join-Path $installed 'improvement-manifest.json') -Raw | ConvertFrom-Json).version -eq $initialOptionalVersion) 'Previous optional manifest not restored.'
Assert ((Get-Content -LiteralPath (Join-Path $installed 'runtime/shortsflow_improvements/__init__.py') -Raw) -eq $original) 'Previous optional code not restored.'
VerifyStable
$rejected=$false
Add-Content -LiteralPath $runtime -Value '# tampered'
try{& $apply -InstallRoot $install -PackageRoot $package -CheckOnly}catch{$rejected=$true}
Assert $rejected 'Tampered optional payload accepted.'
$entry=$manifest.files[0]
$entry.path='../workspace/token.json'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $package 'improvement-manifest.json')
$rejected=$false
try{& $apply -InstallRoot $install -PackageRoot $package -CheckOnly}catch{$rejected=$true}
Assert $rejected 'Protected target accepted.'
VerifyStable
Write-Output 'PASS: optional install/check-only, prerequisite/active-app guards, failed-install recovery, first disable, version rollback, checksum rejection, protected paths, stable code/version/schedules/login/model preservation.'
