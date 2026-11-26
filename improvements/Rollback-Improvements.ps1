$ErrorActionPreference='Stop'
$addon=$PSScriptRoot
$root=Split-Path -Parent $addon
$installed=Join-Path $addon 'state/installed.json'
if(-not(Test-Path -LiteralPath $installed)){throw 'There is no installed optional improvement to roll back.'}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match 'shortsflow_improvements'})
if($running.Count){throw 'Let active jobs finish, then use STOP-IMPROVEMENTS.cmd before rolling back.'}
$info=Get-Content -LiteralPath $installed -Raw | ConvertFrom-Json
$backup=[IO.Path]::GetFullPath([string]$info.backup)
$backupRoot=[IO.Path]::GetFullPath((Join-Path $addon 'backups'))+[IO.Path]::DirectorySeparatorChar
if(-not $backup.StartsWith($backupRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Backup path is outside the optional folder.'}
if($info.previous -and (Test-Path -LiteralPath (Join-Path $backup 'installed.json'))){
 foreach($file in (Get-ChildItem -LiteralPath $backup -File -Recurse)){
  $relative=$file.FullName.Substring($backup.Length+1)
  if($relative -in @('installed.json','improvement-manifest.json')){continue}
  if($relative.Replace([char]92,[char]47) -notmatch '^(runtime/shortsflow_improvements/[A-Za-z0-9_]+[.]py|[A-Za-z0-9_-]+[.](cmd|ps1|txt))$'){throw 'Unexpected backup target.'}
  $target=[IO.Path]::GetFullPath((Join-Path $addon $relative))
  if(-not $target.StartsWith([IO.Path]::GetFullPath($addon)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Backup target leaves optional folder.'}
  Copy-Item -LiteralPath $file.FullName -Destination $target -Force
 }
 Copy-Item -LiteralPath (Join-Path $backup 'installed.json') -Destination $installed -Force
 $savedManifest=Join-Path $backup 'improvement-manifest.json'
 if(Test-Path -LiteralPath $savedManifest){Copy-Item -LiteralPath $savedManifest -Destination (Join-Path $addon 'improvement-manifest.json') -Force}
 Write-Host 'Previous optional improvement version restored. Normal stable app unchanged.'
}else{
 $info.enabled=$false
 $info | ConvertTo-Json | Set-Content -LiteralPath $installed -Encoding UTF8
 Write-Host 'Optional improvements disabled. Normal RUN-SHORTSFLOW.cmd uses the stable app.'
}
Write-Host 'Videos, subtitle correction files, account sign-in and saved jobs were preserved. No app was started automatically.'
