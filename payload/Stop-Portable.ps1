$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$state = Join-Path $root 'logs/ui.pid'
if (Test-Path -LiteralPath $state) {
    $savedId = 0
    if ([int]::TryParse((Get-Content -LiteralPath $state -Raw).Trim(), [ref]$savedId)) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$savedId" -ErrorAction SilentlyContinue
        $launcher = Join-Path $root 'Portable.ps1'
        if ($p -and $p.CommandLine -and $p.CommandLine.IndexOf($launcher, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            & taskkill.exe /PID $savedId /T /F
        }
    }
}
# Stop only the Ollama binary belonging to this portable folder.
$expectedOllama = Join-Path $root 'ollama\ollama.exe'
Get-CimInstance Win32_Process -Filter "Name='ollama.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -eq $expectedOllama } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
Write-Host 'Portable ShortsFlow stopped.'
