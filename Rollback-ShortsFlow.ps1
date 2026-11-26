param([string]$InstallRoot=$PSScriptRoot,[string]$BackupPath,[switch]$NoRestart)
$ErrorActionPreference='Stop'
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
$backupRoot=Join-Path $InstallRoot 'update-backups'
if(-not $BackupPath){
 $latest=Get-ChildItem -LiteralPath $backupRoot -Directory | Where-Object {Test-Path -LiteralPath (Join-Path $_.FullName 'venv/Lib/site-packages/shortsflow/webui.py')} | Sort-Object Name -Descending | Select-Object -First 1
 if(-not $latest){throw 'No previous update backup was found.'}
 $BackupPath=$latest.FullName
}
$BackupPath=[IO.Path]::GetFullPath($BackupPath)
if(-not $BackupPath.StartsWith([IO.Path]::GetFullPath($backupRoot)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Choose a backup inside this installation update-backups folder.'}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)})
if($running.Count){throw 'Close ShortsFlow first. Let active uploads or video processing finish, then run rollback again.'}
$files=@(Get-ChildItem -LiteralPath $BackupPath -File -Recurse | Where-Object {$_.Extension -in @('.py','.ps1','.cmd','.txt')})
if(-not $files.Count){throw 'The selected backup contains no code files.'}
$stage=Join-Path $InstallRoot ('temp/rollback-package-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage -Force | Out-Null
$entries=@()
foreach($file in $files){
 $relative=$file.FullName.Substring($BackupPath.Length+1).Replace([char]92,[char]47)
 # Keep the rollback utility available after returning to an older version.
 if($relative -in @('Rollback-ShortsFlow.ps1','ROLLBACK-SHORTSFLOW.cmd')){continue}
 $dest=Join-Path $stage ('saved/'+$relative)
 New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
 Copy-Item -LiteralPath $file.FullName -Destination $dest
 $entries+=@{source='saved/'+$relative;target=$relative;sha256=(Get-FileHash -LiteralPath $dest).Hash.ToLowerInvariant();bytes=$file.Length}
}
$version='rollback-'+(Split-Path -Leaf $BackupPath)
$oldVersion=Join-Path $BackupPath 'previous-version.json'
if(Test-Path -LiteralPath $oldVersion){$version=(Get-Content -LiteralPath $oldVersion -Raw | ConvertFrom-Json).version}
@{schema=1;version=$version;upstream_version='0.9.4';files=$entries} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stage 'update-manifest.json') -Encoding UTF8
Write-Output ('Restoring code from: '+$BackupPath)
& (Join-Path $InstallRoot 'Apply-ShortsFlow-Update.ps1') -InstallRoot $InstallRoot -PackageRoot $stage -NoRestart:$NoRestart
Write-Output 'Previous code restored. Videos, models, YouTube sign-in and scheduled jobs were preserved.'
