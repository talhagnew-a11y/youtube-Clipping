param([string]$PackageRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$apply=Join-Path $PackageRoot 'Apply-ShortsFlow-Update.ps1'
$base=Join-Path ([IO.Path]::GetTempPath()) ('shortsflow-updater-test-'+[Guid]::NewGuid().ToString('N'))
$install=Join-Path $base 'installed'
$package=Join-Path $base 'package'
New-Item -ItemType Directory -Force -Path (Join-Path $install 'venv/Lib/site-packages/shortsflow'),(Join-Path $install 'models'),(Join-Path $install 'workspace'),(Join-Path $install 'config'),$package | Out-Null
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/__init__.py') -Value '__version__ = "0.9.4"'
Set-Content -LiteralPath (Join-Path $install 'Portable.ps1') -Value 'old script'
Set-Content -LiteralPath (Join-Path $install '.env') -Value 'secret sentinel'
Set-Content -LiteralPath (Join-Path $install 'models/model.bin') -Value 'model sentinel'
Set-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Value 'login sentinel'
Set-Content -LiteralPath (Join-Path $install 'config/encoder-profiles.json') -Value 'profile sentinel'
Set-Content -LiteralPath (Join-Path $package 'one.txt') -Value 'new script'
Set-Content -LiteralPath (Join-Path $package 'two.txt') -Value 'help text'
function Manifest($Targets=@('Portable.ps1','HELP.txt')){
 $files=@()
 for($i=0;$i -lt $Targets.Count;$i++){
  $name=@('one.txt','two.txt')[$i]
  $f=Get-Item -LiteralPath (Join-Path $package $name)
  $files+=@{source=$name;target=$Targets[$i];bytes=$f.Length;sha256=(Get-FileHash -LiteralPath $f.FullName).Hash}
 }
 @{schema=1;version='test.1';upstream_version='0.9.4';files=$files} | ConvertTo-Json -Depth 5 |
  Set-Content -LiteralPath (Join-Path $package 'update-manifest.json')
}
function Assert($Condition,$Message){if(-not $Condition){throw $Message}}
Manifest
& $apply -InstallRoot $install -PackageRoot $package -NoRestart
Assert ((Get-Content -LiteralPath (Join-Path $install 'Portable.ps1') -Raw).Trim() -eq 'new script') 'Install failed.'
Assert ((Get-Content -LiteralPath (Join-Path $install '.env') -Raw).Trim() -eq 'secret sentinel') 'Secret was changed.'
Assert ((Get-Content -LiteralPath (Join-Path $install 'models/model.bin') -Raw).Trim() -eq 'model sentinel') 'Model was changed.'
Assert ((Get-Content -LiteralPath (Join-Path $install 'workspace/token.json') -Raw).Trim() -eq 'login sentinel') 'Login was changed.'
Assert ((Get-Content -LiteralPath (Join-Path $install 'config/encoder-profiles.json') -Raw).Trim() -eq 'profile sentinel') 'Laptop profile was changed.'
function Reject($Message){
 $rejected=$false
 try{& $apply -InstallRoot $install -PackageRoot $package -CheckOnly}catch{$rejected=$true}
 Assert $rejected $Message
}
Set-Content -LiteralPath (Join-Path $package 'one.txt') -Value 'tampered'
Reject 'Checksum mismatch was accepted.'
Manifest @('../escape.txt','HELP.txt')
Reject 'Path traversal was accepted.'
Manifest @('workspace/token.json','HELP.txt')
Reject 'Protected user file was accepted.'
Manifest
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/__init__.py') -Value '__version__ = "0.9.5"'
Reject 'Wrong upstream version was accepted.'
Set-Content -LiteralPath (Join-Path $install 'venv/Lib/site-packages/shortsflow/__init__.py') -Value '__version__ = "0.9.4"'
Set-Content -LiteralPath (Join-Path $install 'LOCKED.txt') -Value 'locked old content'
Set-Content -LiteralPath (Join-Path $package 'one.txt') -Value 'must roll back'
Manifest @('Portable.ps1','LOCKED.txt')
$lock=[IO.File]::Open((Join-Path $install 'LOCKED.txt'),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
$rolledBack=$false
try{try{& $apply -InstallRoot $install -PackageRoot $package -NoRestart}catch{$rolledBack=$true}}finally{$lock.Dispose()}
Assert $rolledBack 'Locked destination did not trigger rollback.'
Assert ((Get-Content -LiteralPath (Join-Path $install 'Portable.ps1') -Raw).Trim() -eq 'new script') 'Rollback did not restore previous code.'
Write-Output 'PASS: install, backup, user-data preservation, checksum rejection, traversal rejection, protected paths, version guard, and rollback.'
Write-Output "Temporary test fixtures: $base"

$authPath=Join-Path $base 'dummy-auth.dpapi'
$dummy=ConvertTo-SecureString 'dummy-test-only' -AsPlainText -Force
$dummy | ConvertFrom-SecureString | Set-Content -LiteralPath $authPath -Encoding Ascii
$restored=(Get-Content -LiteralPath $authPath -Raw).Trim() | ConvertTo-SecureString
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($restored)
try{Assert ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) -eq 'dummy-test-only') 'Encrypted login could not be reloaded.'}
finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
Write-Output 'PASS: encrypted Windows login round-trip, including file newline.'
