param([string]$InstallRoot=$PSScriptRoot,[switch]$ListOnly)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($InstallRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
function Is-OwnedShortsFlowUi($Process,[string]$RootPath){
 if(-not $Process.ExecutablePath -or -not $Process.CommandLine){return $false}
 $prefix=$RootPath.TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar
 if(-not $Process.ExecutablePath.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){return $false}
 return ($Process.Name -match '^python(w)?[.]exe$' -and ($Process.CommandLine -match '-m\s+shortsflow[.]cli\s+webui(?:\s|$)' -or $Process.CommandLine -match '[\\/]shortsflow[\\/]webui[.]py(?:"|\s|$)'))
}
$processes=@(Get-CimInstance Win32_Process -ErrorAction Stop)
$uis=@($processes | Where-Object {Is-OwnedShortsFlowUi $_ $root})
if($ListOnly){return $uis}
foreach($process in $uis){
 Write-Host ('Stopping ShortsFlow app '+$process.ProcessId)
 & taskkill.exe /PID $process.ProcessId /T /F | Out-Host
}
# Launcher IDs are only a fallback; discovery above also finds orphaned UI processes.
$state=Join-Path $root 'logs/ui.pid'
if(Test-Path -LiteralPath $state){
 $savedId=0
 if([int]::TryParse((Get-Content -LiteralPath $state -Raw).Trim(),[ref]$savedId)){
  $launcher=Join-Path $root 'Portable.ps1'
  $process=$processes | Where-Object {$_.ProcessId -eq $savedId} | Select-Object -First 1
  if($process -and $process.CommandLine -and $process.CommandLine.IndexOf($launcher,[StringComparison]::OrdinalIgnoreCase) -ge 0){
   & taskkill.exe /PID $savedId /T /F | Out-Host
  }
 }
}
$expectedOllama=Join-Path $root 'ollama/ollama.exe'
foreach($process in $processes){
 if($process.Name -eq 'ollama.exe' -and $process.ExecutablePath -eq $expectedOllama){Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue}
}
$remaining=@(Get-CimInstance Win32_Process | Where-Object {Is-OwnedShortsFlowUi $_ $root})
if($remaining.Count){throw 'ShortsFlow is still running. Run STOP-SHORTSFLOW.cmd as administrator on this laptop.'}
if(Test-Path -LiteralPath $state){Remove-Item -LiteralPath $state -Force}
Write-Host 'Verified: no ShortsFlow app remains running from this folder.'
