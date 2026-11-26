param([Parameter(Mandatory=$true)][string]$InstallRoot,[Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference='Stop'
if($Version -notmatch '^\d{4}[.]\d{2}[.]\d{2}[.]\d+$'){throw 'Version format: YYYY.MM.DD.revision'}
$repo=$PSScriptRoot
$versionFile=Join-Path $InstallRoot 'venv/Lib/site-packages/shortsflow/__init__.py'
if((Get-Content -LiteralPath $versionFile -Raw) -notmatch '__version__\s*=\s*["'']0[.]9[.]4["'']'){throw 'This overlay builder supports ShortsFlow 0.9.4 only.'}
$payload=Join-Path $repo 'payload'
$rootFiles=@('Rollback-ShortsFlow.ps1','ROLLBACK-SHORTSFLOW.cmd','Portable.ps1','Stop-Portable.ps1','RUN-SHORTSFLOW.cmd','STOP-SHORTSFLOW.cmd','CHECK-SETUP.cmd','SHORTSFLOW-CLI.cmd','FAST-SHORTSFLOW.cmd','HIGH-QUALITY-SHORTSFLOW.cmd','RESUME-LAST-VIDEO.cmd','Resume-Last-Video.ps1','COMPARE-CPU-INTEL.cmd','COMPARE-CPU-INTEL.ps1','TEST-GPU.cmd','TEST-GPU.ps1','PORTABLE-HELP.txt','CPU-INTEL-HELP.txt','FAST-SETTINGS-AND-COPY.txt','I7-FINAL-SETTINGS.txt','LOCAL-CHANGES.txt','ShortsFlow.cmd','ShortsFlow Terminal.cmd')
foreach($name in $rootFiles){Copy-Item -LiteralPath (Join-Path $InstallRoot $name) -Destination (Join-Path $payload $name) -Force}
foreach($name in @('Apply-ShortsFlow-Update.ps1','Update-ShortsFlow.ps1','UPDATE-SHORTSFLOW.cmd','UPDATE-FROM-ZIP.cmd')){Copy-Item -LiteralPath (Join-Path $repo $name) -Destination (Join-Path $payload $name) -Force}
foreach($name in @('gpu-test.py','compare-cpu-intel.py','portable-check.py')){Copy-Item -LiteralPath (Join-Path $InstallRoot ('tools/'+$name)) -Destination (Join-Path $payload ('tools/'+$name)) -Force}
foreach($name in @('engine/analysis.py','engine/script_gen.py','engine/remotion_renderer.py','engine/video_gen.py','engine/portable_fast.py','engine/portable_encoder.py','shortsflow/_main.py','shortsflow/webui.py','shortsflow/settings.py')){
 Copy-Item -LiteralPath (Join-Path $InstallRoot ('venv/Lib/site-packages/'+$name)) -Destination (Join-Path $payload ('venv/Lib/site-packages/'+$name)) -Force
}
Copy-Item -LiteralPath (Join-Path $repo 'LICENSE') -Destination (Join-Path $payload 'LICENSE-ShortsFlow.txt') -Force
$entries=@(Get-ChildItem -LiteralPath $payload -File -Recurse | Sort-Object FullName | ForEach-Object {
 $relative=$_.FullName.Substring($payload.Length+1).Replace([char]92,[char]47)
 if($_.Length -gt 2MB){throw "Heavy file refused: $relative"}
 if($_.Extension -notin @('.py','.ps1','.cmd','.txt')){throw "Unexpected payload type: $relative"}
 @{source='payload/'+$relative;target=$relative;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant();bytes=$_.Length}
})
@{schema=1;version=$Version;upstream_version='0.9.4';repository='talhagnew-a11y/youtube-Clipping';files=$entries} |
 ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $repo 'update-manifest.json') -Encoding UTF8
& (Join-Path $repo 'Apply-ShortsFlow-Update.ps1') -InstallRoot $InstallRoot -PackageRoot $repo -CheckOnly
