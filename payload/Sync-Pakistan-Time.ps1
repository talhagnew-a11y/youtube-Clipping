param([switch]$Setup,[switch]$RequestAdmin)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if($RequestAdmin){
 $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
 if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
  Start-Process -FilePath powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Setup') | Out-Null
  return
 }
 $Setup=$true
}
$log=Join-Path $root 'logs/pakistan-time.log'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null
try{
 if((Get-TimeZone).Id -ne 'Pakistan Standard Time'){
  & tzutil.exe /s 'Pakistan Standard Time'
  if($LASTEXITCODE -ne 0){throw 'Windows denied the timezone change.'}
 }
 if($Setup){
  Set-Service -Name W32Time -StartupType Automatic
  Start-Service -Name W32Time
  & w32tm.exe /config '/manualpeerlist:time.windows.com,0x8 time.cloudflare.com,0x8' /syncfromflags:manual /update | Out-Null
  if($LASTEXITCODE -ne 0){throw 'Windows time configuration failed.'}
  & w32tm.exe /resync /force | Out-Null
  if($LASTEXITCODE -ne 0){throw 'Clock sync failed. Check internet and run FIX-PAKISTAN-TIME.cmd again.'}
  'Pakistan timezone and Windows automatic clock synchronization configured.' | Set-Content -LiteralPath $log
 }else{
  # Non-blocking best effort on every launch; no repeated administrator prompts.
  $result=& w32tm.exe /resync /nowait 2>&1
  if($LASTEXITCODE -ne 0){
   'Pakistan timezone selected. For reliable automatic clock synchronization, run FIX-PAKISTAN-TIME.cmd once and allow Windows administrator permission.' | Set-Content -LiteralPath $log
  }else{'Pakistan timezone selected; Windows clock synchronization requested.' | Set-Content -LiteralPath $log}
 }
}catch{
 ('Clock setup: '+$_.Exception.Message+' Run FIX-PAKISTAN-TIME.cmd once.') | Set-Content -LiteralPath $log
 if($Setup){throw}
}
