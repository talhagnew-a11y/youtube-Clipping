param(
 [string]$InstallRoot,
 [string]$PackageRoot=$PSScriptRoot,
 [switch]$CheckOnly,
 [switch]$NoRestart
)
$ErrorActionPreference='Stop'
function ChildPath([string]$Base,[string]$Relative){
 $baseFull=[IO.Path]::GetFullPath($Base).TrimEnd([IO.Path]::DirectorySeparatorChar)
 if([IO.Path]::IsPathRooted($Relative)){throw 'Absolute paths are not allowed in the manifest.'}
 $path=[IO.Path]::GetFullPath((Join-Path $baseFull $Relative))
 if(-not $path.StartsWith($baseFull+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Manifest path leaves its intended folder.'}
 return $path
}
function AllowedTarget([string]$Path){
 $p=$Path.Replace([char]92,[char]47)
 if($p -match '^(venv/Lib/site-packages/(engine|shortsflow)/[A-Za-z0-9_]+[.]py|tools/[A-Za-z0-9_-]+[.]py)$'){return $true}
 return ($p -notmatch '/' -and $p -match '^[A-Za-z0-9 _-]+[.](ps1|cmd|txt)$')
}
function AtomicCopy([string]$From,[string]$To){
 $dir=Split-Path -Parent $To
 New-Item -ItemType Directory -Force -Path $dir | Out-Null
 $pending=Join-Path $dir ([IO.Path]::GetRandomFileName()+'.update')
 try {
  Copy-Item -LiteralPath $From -Destination $pending
  if(Test-Path -LiteralPath $To){[IO.File]::Replace($pending,$To,[NullString]::Value)}
  else{Move-Item -LiteralPath $pending -Destination $To}
 }finally{if(Test-Path -LiteralPath $pending){Remove-Item -LiteralPath $pending -Force}}
}
if(-not $InstallRoot){throw 'Choose the existing shortsflow folder first.'}
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot)
$manifestPath=Join-Path $PackageRoot 'update-manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($manifest.schema -ne 1){throw 'Unsupported update format.'}
$versionFile=Join-Path $InstallRoot 'venv/Lib/site-packages/shortsflow/__init__.py'
if(-not(Test-Path -LiteralPath $versionFile)){throw 'This is not an existing portable ShortsFlow installation.'}
$versionText=Get-Content -LiteralPath $versionFile -Raw
if($versionText -notmatch '__version__\s*=\s*["'']([^"'']+)["'']'){throw 'Cannot identify installed ShortsFlow version.'}
if($Matches[1] -ne $manifest.upstream_version){throw "This update needs ShortsFlow $($manifest.upstream_version); installed version is $($Matches[1])."}
$items=@()
$seen=@{}
foreach($entry in $manifest.files){
 if(-not(AllowedTarget $entry.target)){throw "Protected or unsupported update target: $($entry.target)"}
 $source=ChildPath $PackageRoot $entry.source
 $target=ChildPath $InstallRoot $entry.target
 if($seen.ContainsKey($target.ToLowerInvariant())){throw 'Duplicate update target.'}
 $seen[$target.ToLowerInvariant()]=$true
 if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "Missing package file: $($entry.source)"}
 if((Get-Item -LiteralPath $source).Length -ne $entry.bytes){throw "Wrong package size: $($entry.source)"}
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $entry.sha256){throw "Package checksum failed: $($entry.source)"}
 if((Test-Path -LiteralPath $target) -and -not(Test-Path -LiteralPath $target -PathType Leaf)){throw "Update target is a directory: $($entry.target)"}
 $items+=@{source=$source;target=$target;relative=$entry.target;existed=(Test-Path -LiteralPath $target -PathType Leaf)}
}
if(-not $items.Count){throw 'Empty update package.'}
if($CheckOnly){Write-Output "Verified $($items.Count) lightweight files, update $($manifest.version). No files changed.";return}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction Stop |
 Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match '--source_video' })
if($running.Count){throw 'A video is processing. Wait for it to finish, or stop it in ShortsFlow, then update. No files changed.'}
$backup=ChildPath $InstallRoot ('update-backups/'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Force -Path $backup | Out-Null
foreach($item in $items){
 if($item.existed){
  $copy=ChildPath $backup $item.relative
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $copy) | Out-Null
  Copy-Item -LiteralPath $item.target -Destination $copy
  $item.backup=$copy
 }
}
$stop=Join-Path $InstallRoot 'Stop-Portable.ps1'
if(Test-Path -LiteralPath $stop){& $stop | Out-Host}
$applied=New-Object System.Collections.Generic.List[object]
try {
 foreach($item in $items){AtomicCopy $item.source $item.target;$applied.Add($item)}
 @{version=$manifest.version;upstream_version=$manifest.upstream_version;files=$items.Count;applied_at=(Get-Date -Format o)} |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallRoot 'UPDATE-VERSION.json') -Encoding UTF8
}catch{
 $cause=$_.Exception.Message
 for($i=$applied.Count-1;$i -ge 0;$i--){
  $item=$applied[$i]
  try{
   if($item.existed){AtomicCopy $item.backup $item.target}
   elseif(Test-Path -LiteralPath $item.target){Remove-Item -LiteralPath $item.target -Force}
  }catch{Write-Warning "Could not restore $($item.relative). Backup: $backup"}
 }
 throw "Update failed; changed files were rolled back. $cause"
}
Write-Output "Updated to $($manifest.version). Models, videos, settings and sign-ins were preserved."
Write-Output "Backup: $backup"
if(-not $NoRestart){
 $launcher=Join-Path $InstallRoot 'Portable.ps1'
 Start-Process -FilePath 'powershell.exe' -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$launcher+'"') -WorkingDirectory $InstallRoot -WindowStyle Hidden | Out-Null
}

