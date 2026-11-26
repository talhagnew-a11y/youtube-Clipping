param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$addon=$PSScriptRoot
$root=Split-Path -Parent $addon
$marker=Join-Path $addon 'state/installed.json'
if(-not(Test-Path -LiteralPath $marker) -or -not (Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).enabled){throw 'Optional improvements are not enabled. Use INSTALL-IMPROVEMENTS.cmd or UPDATE-IMPROVEMENTS.cmd first.'}
$running=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and $_.CommandLine -match 'webui|shortsflow_improvements[.]bootstrap'})
if($running.Count){throw 'ShortsFlow is already running. Let jobs finish, then use the matching STOP command before starting test mode.'}
$env:SHORTSFLOW_IMPROVEMENTS_STATE=Join-Path $addon 'state'
$base=Get-Content -LiteralPath (Join-Path $root 'Portable.ps1') -Raw
$rootLiteral="'"+$root.Replace("'","''")+"'"
$runtimeLiteral="'"+(Join-Path $addon 'runtime').Replace("'","''")+"'"
$rootMarker='$root = $PSScriptRoot'
$pathMarker='$env:PYTHONPATH = Join-Path $root ''venv\Lib\site-packages'''
$commandMarker='-m shortsflow.cli webui --open'
if(-not $base.Contains($rootMarker) -or -not $base.Contains($pathMarker) -or -not $base.Contains($commandMarker)){throw 'Stable launcher changed; update the optional package for this base version.'}
# Adapt the existing portable environment IN MEMORY. No installed stable file is edited.
$base=$base.Replace($rootMarker,('$root = '+$rootLiteral))
$base=$base.Replace($pathMarker,('$env:PYTHONPATH = (Join-Path $root ''venv\Lib\site-packages'') + '';'' + '+$runtimeLiteral))
$base=$base.Replace($commandMarker,'-m shortsflow_improvements.bootstrap --open')
$tokens=$null;$errors=$null
$null=[Management.Automation.Language.Parser]::ParseInput($base,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
if($CheckOnly){Write-Output 'Verified optional bootstrap, runtime path and stable launcher adaptation. No app started; stable launcher unchanged.';return}
& ([scriptblock]::Create($base)) -Mode webui
