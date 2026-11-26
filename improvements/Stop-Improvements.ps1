$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match '-m\s+shortsflow_improvements[.]bootstrap(?:\s|$)'})
foreach($process in $running){& taskkill.exe /PID $process.ProcessId /T /F | Out-Host}
Write-Host 'Optional improvements app stopped. Use the normal RUN-SHORTSFLOW.cmd for stable mode.'
