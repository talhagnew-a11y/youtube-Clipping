param([string]$PackageRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$path=Join-Path $PackageRoot 'payload/Stop-Portable.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Is-OwnedShortsFlowUi'},$true)
Invoke-Expression $function.Extent.Text
$root='D:\shortsflow'
$cases=@(
 @{exe='D:\shortsflow\python\python.exe';name='python.exe';cmd='python -m shortsflow.cli webui --open';owned=$true},
 @{exe='D:\shortsflow\python\python.exe';name='python.exe';cmd='python -m shortsflow.cli webui';owned=$true},
 @{exe='D:\shortsflow-other\python.exe';name='python.exe';cmd='python -m shortsflow.cli webui';owned=$false},
 @{exe='C:\Python\python.exe';name='python.exe';cmd='python -m shortsflow.cli webui';owned=$false},
 @{exe='D:\shortsflow\python\python.exe';name='python.exe';cmd='python -m shortsflow.cli --source_video movie.mp4';owned=$false},
 @{exe='D:\shortsflow\python\python.exe';name='python.exe';cmd='python other.py';owned=$false}
)
foreach($case in $cases){
 $process=[pscustomobject]@{ExecutablePath=$case.exe;Name=$case.name;CommandLine=$case.cmd}
 if((Is-OwnedShortsFlowUi $process $root) -ne $case.owned){throw ('Ownership check failed: '+$case.cmd)}
}
Write-Output 'PASS: orphaned UI found without PID file; unrelated Python apps and other installations excluded.'
