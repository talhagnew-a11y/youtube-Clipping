param([string]$PackageZip,[switch]$CheckOnly,[switch]$NoRestart,[switch]$RefreshLogin)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$root=$PSScriptRoot
if(-not(Test-Path -LiteralPath (Join-Path $root 'venv/Lib/site-packages/shortsflow/__init__.py'))){throw 'Keep this updater in your existing shortsflow folder.'}
$stage=Join-Path $root ('temp/update-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage | Out-Null
if($PackageZip){
 Copy-Item -LiteralPath $PackageZip -Destination (Join-Path $stage 'update.zip')
}else{
 $authDir=Join-Path $root '.update-auth'
 New-Item -ItemType Directory -Force -Path $authDir | Out-Null
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 $machine=(Get-ItemProperty -LiteralPath 'HKLM:/SOFTWARE/Microsoft/Cryptography' -Name MachineGuid).MachineGuid
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$id=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($identity+'|'+$machine)))).Replace('-','').Substring(0,20)}
 finally{$sha.Dispose()}
 $saved=Join-Path $authDir ($id+'.dpapi')
 $secure=$null
 if(-not $RefreshLogin -and (Test-Path -LiteralPath $saved)){
  try{$secure=Get-Content -LiteralPath $saved -Raw | ConvertTo-SecureString}catch{}
 }
 if(-not $secure){
  Write-Host 'This GitHub repo is private. One-time access is needed on this Windows account.'
  Write-Host 'Create a fine-grained GitHub token for ONLY talhagnew-a11y/youtube-Clipping, Contents: Read-only.'
  Write-Host 'Help: https://github.com/settings/personal-access-tokens/new'
  $secure=Read-Host 'Paste the read-only token (hidden)' -AsSecureString
 }
 $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
 try{$token=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}
 finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
 if(-not $token){throw 'No GitHub token was supplied.'}
 $headers=@{Authorization=('Bearer '+$token);Accept='application/vnd.github+json';'User-Agent'='ShortsFlow-Portable-Updater'}
 try{
  Invoke-WebRequest -Uri 'https://api.github.com/repos/talhagnew-a11y/youtube-Clipping/zipball/main' -Headers $headers -OutFile (Join-Path $stage 'update.zip') -UseBasicParsing
 }catch{
  throw 'GitHub download failed. Check internet, repository access and token expiry. Use the ZIP update option if preferred.'
 }finally{$headers=$null;$token=$null}
 $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $saved -Encoding Ascii
}
Expand-Archive -LiteralPath (Join-Path $stage 'update.zip') -DestinationPath (Join-Path $stage 'package')
$manifest=Get-ChildItem -LiteralPath (Join-Path $stage 'package') -Filter update-manifest.json -File -Recurse | Select-Object -First 1
if(-not $manifest){throw 'This ZIP is not a ShortsFlow update package.'}
$apply=Join-Path $manifest.DirectoryName 'Apply-ShortsFlow-Update.ps1'
if(-not(Test-Path -LiteralPath $apply)){throw 'Update installer is missing.'}
& $apply -InstallRoot $root -PackageRoot $manifest.DirectoryName -CheckOnly:$CheckOnly -NoRestart:$NoRestart
