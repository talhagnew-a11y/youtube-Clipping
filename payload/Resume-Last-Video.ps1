param([switch]$Preview)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$commandFile=Get-ChildItem -LiteralPath (Join-Path $root 'workspace\sessions') -Filter command.json -File -Recurse |
 Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(-not $commandFile){throw 'No previous video run was found.'}
$session=$commandFile.DirectoryName
$recordFile=Join-Path $session 'resume-source.json'
if(-not(Test-Path -LiteralPath $recordFile)){throw 'This run has no preserved input yet. Open Earlier runs in ShortsFlow to continue it.'}
$record=Get-Content -LiteralPath $recordFile -Raw | ConvertFrom-Json
$saved=Get-Content -LiteralPath $commandFile.FullName -Raw | ConvertFrom-Json
$argsList=@($saved.cmd | Select-Object -Skip 3 | ForEach-Object {
 if($_.StartsWith($record.original_root+'\',[StringComparison]::OrdinalIgnoreCase)){
  Join-Path $root $_.Substring($record.original_root.Length+1)
 }else{$_}
})
if($argsList -notcontains '--use_cache'){$argsList+='--use_cache'}
if($Preview){
 Write-Output "Resume session: $session"
 Write-Output 'Reuses saved transcription, highlights, segments, and completed clip cache.'
 Write-Output ($argsList -join ' ')
 return
}
$running=Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
 Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($session,[StringComparison]::OrdinalIgnoreCase) -ge 0 }
if($running){Write-Host 'This video is already processing. Let it finish; no duplicate job started.';return}
$source=Join-Path $root $record.original_relative
$backup=Join-Path $root $record.backup_relative
if(-not(Test-Path -LiteralPath $source)){
 New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($source)) | Out-Null
 Copy-Item -LiteralPath $backup -Destination $source
}
if(-not(Test-Path -LiteralPath (Join-Path $session 'results.json'))){
 & (Join-Path $root 'Portable.ps1') -Mode cli -CliArgs $argsList
 if($LASTEXITCODE -ne 0){throw 'Resume stopped with an error. Completed clips are kept in the session folder.'}
}
$destination=Join-Path $root $record.output_relative
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Get-ChildItem -LiteralPath $session -File |
 Where-Object { $_.Name -match '^(video_clip_.*\.(mp4|jpg|png|srt|ass|vtt)|metadata\.json|results\.json|clip_report\.md)$' } |
 ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $destination -Force }
Write-Host "Saved finished clips to $destination"
