param([string]$InstallRoot,[string]$PackageRoot=$PSScriptRoot,[switch]$CheckOnly)
$ErrorActionPreference='Stop'
if(-not $InstallRoot){
 $candidate=Split-Path -Parent $PSScriptRoot
 if(Test-Path -LiteralPath (Join-Path $candidate 'venv/Lib/site-packages/shortsflow/__init__.py')){$InstallRoot=$candidate}
 else{
  Add-Type -AssemblyName System.Windows.Forms
  $picker=New-Object System.Windows.Forms.FolderBrowserDialog
  $picker.Description='Choose the existing shortsflow installation. Install the NORMAL full-video/hashtag update first.'
  if($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){return}
  $InstallRoot=$picker.SelectedPath
 }
}
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot)
$targetRoot=Join-Path $InstallRoot 'improvements'
function SafeChild([string]$Base,[string]$Relative){
 $baseFull=[IO.Path]::GetFullPath($Base).TrimEnd([IO.Path]::DirectorySeparatorChar)
 if([IO.Path]::IsPathRooted($Relative)){throw 'Absolute package paths are refused.'}
 $path=[IO.Path]::GetFullPath((Join-Path $baseFull $Relative))
 if(-not $path.StartsWith($baseFull+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Package path leaves its intended folder.'}
 return $path
}
function IsCode([string]$Relative){
 $p=$Relative.Replace([char]92,[char]47)
 return ($p -match '^runtime/shortsflow_improvements/[A-Za-z0-9_]+[.]py$' -or $p -match '^[A-Za-z0-9_-]+[.](cmd|ps1|txt)$')
}
$manifestPath=Join-Path $PackageRoot 'improvement-manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($manifest.schema -ne 1 -or $manifest.kind -ne 'optional-improvements'){throw 'Wrong optional package format.'}
$versionPath=Join-Path $InstallRoot 'UPDATE-VERSION.json'
if(-not(Test-Path -LiteralPath $versionPath)){throw 'Install the NORMAL update first (INSTALL-UPDATE.cmd from the repository root). No files changed.'}
$baseVersion=(Get-Content -LiteralPath $versionPath -Raw | ConvertFrom-Json).version
if([version]$baseVersion -lt [version]$manifest.required_base){throw "Normal update $($manifest.required_base) or newer is required first. Improvements were NOT installed."}
foreach($baseFile in $manifest.base_files){
 $path=SafeChild $InstallRoot $baseFile.path
 if(-not(Test-Path -LiteralPath $path) -or (Get-FileHash -LiteralPath $path).Hash -ne $baseFile.sha256){throw 'The stable app differs from the tested base. Install the normal update first; stable files were not changed.'}
}
$files=@();$seen=@{}
foreach($entry in $manifest.files){
 if(-not(IsCode $entry.path)){throw 'Protected or unsupported optional target.'}
 $source=SafeChild $PackageRoot $entry.path
 $target=SafeChild $targetRoot $entry.path
 if($seen.ContainsKey($target.ToLowerInvariant())){throw 'Duplicate optional target.'}
 $seen[$target.ToLowerInvariant()]=$true
 if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw 'Missing optional package file.'}
 if((Get-Item -LiteralPath $source).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $source).Hash -ne $entry.sha256){throw 'Optional package checksum failed.'}
 $files+=@{source=$source;target=$target;relative=$entry.path;existed=(Test-Path -LiteralPath $target -PathType Leaf)}
}
if(-not $files.Count){throw 'Empty optional package.'}
if($CheckOnly){Write-Output "Verified optional improvements $($manifest.version): $($files.Count) files. Stable update remains $baseVersion.";return}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match 'webui|shortsflow_improvements[.]bootstrap|--source_video'})
if($running.Count){throw 'Let active jobs finish, then stop ShortsFlow before installing optional improvements. No files changed.'}
New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
$state=Join-Path $targetRoot 'state'
New-Item -ItemType Directory -Force -Path $state | Out-Null
$installed=Join-Path $state 'installed.json'
$backup=Join-Path $targetRoot ('backups/'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Force -Path $backup | Out-Null
$previous=$null
if(Test-Path -LiteralPath $installed){$previous=Get-Content -LiteralPath $installed -Raw | ConvertFrom-Json;Copy-Item -LiteralPath $installed -Destination (Join-Path $backup 'installed.json')}
$installedManifest=Join-Path $targetRoot 'improvement-manifest.json'
$oldManifest=Join-Path $backup 'improvement-manifest.json'
if(Test-Path -LiteralPath $installedManifest){Copy-Item -LiteralPath $installedManifest -Destination $oldManifest}
foreach($file in $files){
 if($file.existed){$saved=SafeChild $backup $file.relative;New-Item -ItemType Directory -Force -Path (Split-Path -Parent $saved) | Out-Null;Copy-Item -LiteralPath $file.target -Destination $saved;$file.backup=$saved}
}
$applied=New-Object System.Collections.Generic.List[object]
try{
 foreach($file in $files){
  if([IO.Path]::GetFullPath($file.source) -eq [IO.Path]::GetFullPath($file.target)){continue}
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $file.target) | Out-Null
  Copy-Item -LiteralPath $file.source -Destination $file.target -Force
  $applied.Add($file)
 }
 $installedManifest=Join-Path $targetRoot 'improvement-manifest.json'
 if([IO.Path]::GetFullPath($manifestPath) -ne [IO.Path]::GetFullPath($installedManifest)){Copy-Item -LiteralPath $manifestPath -Destination $installedManifest -Force}
 $queueState=Join-Path $state 'queue.json'
 if(-not(Test-Path -LiteralPath $queueState)){'{"paused":true,"cooldowns":{}}' | Set-Content -LiteralPath $queueState -Encoding UTF8}
 @{enabled=$true;version=$manifest.version;base_version=$baseVersion;backup=$backup;previous=($null -ne $previous);installed_at=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath $installed -Encoding UTF8
}catch{
 for($i=$applied.Count-1;$i -ge 0;$i--){$file=$applied[$i];if($file.existed){Copy-Item -LiteralPath $file.backup -Destination $file.target -Force}else{Remove-Item -LiteralPath $file.target -Force}}
 if(Test-Path -LiteralPath $oldManifest){Copy-Item -LiteralPath $oldManifest -Destination $installedManifest -Force}
 elseif(Test-Path -LiteralPath $installedManifest){Remove-Item -LiteralPath $installedManifest -Force}
 if($previous){Copy-Item -LiteralPath (Join-Path $backup 'installed.json') -Destination $installed -Force}
 throw
}
Write-Output "Optional improvements installed: $($manifest.version). Stable code, normal updater, videos, models, login and schedules were not replaced."
Write-Output "Test only when ready: $targetRoot\RUN-IMPROVEMENTS.cmd"
