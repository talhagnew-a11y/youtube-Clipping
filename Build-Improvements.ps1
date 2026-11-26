param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference='Stop'
if($Version -notmatch '^\d{4}[.]\d{2}[.]\d{2}[.]\d+$'){throw 'Version format: YYYY.MM.DD.revision'}
$folder=Join-Path $PSScriptRoot 'improvements'
$normal=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'update-manifest.json') -Raw | ConvertFrom-Json
$names=@('Apply-Improvements.ps1','Launch-Improvements.ps1','Stop-Improvements.ps1','Rollback-Improvements.ps1','Update-Improvements.ps1','INSTALL-IMPROVEMENTS.cmd','RUN-IMPROVEMENTS.cmd','STOP-IMPROVEMENTS.cmd','ROLLBACK-IMPROVEMENTS.cmd','UPDATE-IMPROVEMENTS.cmd','HELP.txt')
$paths=@($names | ForEach-Object {Join-Path $folder $_})
$paths+=@(Get-ChildItem -LiteralPath (Join-Path $folder 'runtime/shortsflow_improvements') -Filter *.py -File | Select-Object -ExpandProperty FullName)
$files=@($paths | Sort-Object | ForEach-Object {
 $file=Get-Item -LiteralPath $_
 if($file.Length -gt 2MB){throw 'Heavy optional code file refused.'}
 @{path=$file.FullName.Substring($folder.Length+1).Replace([char]92,[char]47);bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()}
})
$base=@('Portable.ps1','venv/Lib/site-packages/shortsflow/webui.py','venv/Lib/site-packages/shortsflow/settings.py','venv/Lib/site-packages/shortsflow/schedule.py','venv/Lib/site-packages/shortsflow/full_editor.py') | ForEach-Object {
 @{path=$_;sha256=(Get-FileHash -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'payload') $_)).Hash.ToLowerInvariant()}
}
$json=@{schema=1;kind='optional-improvements';version=$Version;required_base=$normal.version;base_files=@($base);files=$files} | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText((Join-Path $folder 'improvement-manifest.json'),$json,(New-Object Text.UTF8Encoding($false)))
Write-Output "Built optional package $Version ($($files.Count) lightweight files). Normal update payload and manifest were not changed."
