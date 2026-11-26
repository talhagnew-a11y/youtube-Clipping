param([string]$InstallRoot,[string]$PackageZip,[switch]$CheckOnly,[switch]$RefreshLogin)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
if(-not $InstallRoot){
 $candidate=Split-Path -Parent $PSScriptRoot
 if(Test-Path -LiteralPath (Join-Path $candidate 'venv/Lib/site-packages/shortsflow/__init__.py')){$InstallRoot=$candidate}
 else{
  Add-Type -AssemblyName System.Windows.Forms
  $picker=New-Object System.Windows.Forms.FolderBrowserDialog
  $picker.Description='Choose your existing shortsflow folder for the OPTIONAL improvements update.'
  if($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){return}
  $InstallRoot=$picker.SelectedPath
 }
}
$root=[IO.Path]::GetFullPath($InstallRoot)
if(-not(Test-Path -LiteralPath (Join-Path $root 'venv/Lib/site-packages/shortsflow/__init__.py'))){throw 'Keep this updater in your existing shortsflow folder.'}
$stage=Join-Path $root ('temp/update-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $stage | Out-Null
if($PackageZip){
 Copy-Item -LiteralPath $PackageZip -Destination (Join-Path $stage 'update.zip')
}else{
 $publicDownload=$false
 if(-not $RefreshLogin){
  try{
   $publicHeaders=@{Accept='application/vnd.github+json';'User-Agent'='ShortsFlow-Portable-Updater'}
   $null=Invoke-RestMethod -Uri 'https://api.github.com/repos/talhagnew-a11y/youtube-Clipping' -Headers $publicHeaders -TimeoutSec 20
   Invoke-WebRequest -Uri 'https://api.github.com/repos/talhagnew-a11y/youtube-Clipping/zipball/main' -Headers $publicHeaders -OutFile (Join-Path $stage 'update.zip') -UseBasicParsing -TimeoutSec 180
   $publicDownload=$true
   Write-Host 'Downloaded public repository update. No token needed.'
  }catch{}
 }
 if(-not $publicDownload){
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
  try{$secure=(Get-Content -LiteralPath $saved -Raw).Trim() | ConvertTo-SecureString}catch{}
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
 $token=$token.Trim()
 $secure=ConvertTo-SecureString $token -AsPlainText -Force
 if(-not $token){throw 'No GitHub token was supplied.'}
 if($token -match '\s'){throw 'The token contains spaces or newlines. Paste only the token, without the label, quotes or Markdown.'}
 $headers=@{Authorization=('Bearer '+$token);Accept='application/vnd.github+json';'User-Agent'='ShortsFlow-Portable-Updater'}
 try{
  # A small authenticated request distinguishes permission failures from ZIP network failures.
  $null=Invoke-RestMethod -Uri 'https://api.github.com/repos/talhagnew-a11y/youtube-Clipping' -Headers $headers -TimeoutSec 30
  Invoke-WebRequest -Uri 'https://api.github.com/repos/talhagnew-a11y/youtube-Clipping/zipball/main' -Headers $headers -OutFile (Join-Path $stage 'update.zip') -UseBasicParsing -TimeoutSec 180
 }catch{
  $status=0
  if($_.Exception.Response){try{$status=[int]$_.Exception.Response.StatusCode}catch{}}
  $reason=switch($status){
   401 {'Token invalid or expired. Generate a new token and run REFRESH-UPDATE-LOGIN.cmd.'}
   403 {'GitHub denied access. Check Contents: Read-only, token approval/expiry and GitHub rate limits.'}
   404 {'This token cannot see the private repository. Resource owner must be talhagnew-a11y; select ONLY youtube-Clipping and Contents: Read-only.'}
   429 {'GitHub rate limit reached. Wait and try again.'}
   default {'Connection/download failed. Check internet, VPN/proxy, firewall and this PC clock. Download the repo ZIP and use improvements/INSTALL-IMPROVEMENTS.cmd.'}
  }
  # Never print the exception/request: it may contain an Authorization header.
  $code=if($status){"HTTP $status"}else{'network/TLS error'}
  throw "GitHub update failed ($code). $reason No app files were changed."
 }finally{$headers=$null;$token=$null}

 $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $saved -Encoding Ascii
 }
}
Expand-Archive -LiteralPath (Join-Path $stage 'update.zip') -DestinationPath (Join-Path $stage 'package')
$manifest=Get-ChildItem -LiteralPath (Join-Path $stage 'package') -Filter improvement-manifest.json -File -Recurse | Select-Object -First 1
if(-not $manifest){throw 'This ZIP has no optional improvements package.'}
$apply=Join-Path $manifest.DirectoryName 'Apply-Improvements.ps1'
if(-not(Test-Path -LiteralPath $apply)){throw 'Update installer is missing.'}
& $apply -InstallRoot $root -PackageRoot $manifest.DirectoryName -CheckOnly:$CheckOnly

