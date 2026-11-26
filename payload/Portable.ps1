param([ValidateSet('webui','doctor','cli')][string]$Mode = 'webui', [Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location -LiteralPath $root
foreach ($folder in @('temp','logs','models\ollama','models\torch','models\huggingface','cache','workspace')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root $folder) | Out-Null
}
if ($Mode -eq 'webui') { $PID | Set-Content -LiteralPath (Join-Path $root 'logs/ui.pid') }
if (-not $env:SHORTSFLOW_FAST_MODE) { $env:SHORTSFLOW_FAST_MODE = '1' }
$env:SHORTSFLOW_HOME = Join-Path $root 'workspace'
$env:XDG_CACHE_HOME = Join-Path $root 'cache'
$env:HF_HOME = Join-Path $root 'models\huggingface'
$env:TORCH_HOME = Join-Path $root 'models\torch'
$env:OLLAMA_MODELS = Join-Path $root 'models\ollama'
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
$env:SHORTSFLOW_OLLAMA_NUM_CTX = '4096'
$env:OLLAMA_KEEP_ALIVE = '30s'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:SHORTSFLOW_FORCE_CPU = '1'
$env:OMP_NUM_THREADS = '4'
$env:SHORTSFLOW_WHISPER_MODEL = 'base'
$env:SHORTSFLOW_REMOTION_CONCURRENCY = '1'
$env:TEMP = Join-Path $root 'temp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $root 'cache\npm'
$env:GRADIO_TEMP_DIR = Join-Path $root 'temp\gradio'
$env:GRADIO_ANALYTICS_ENABLED = 'False'
$env:WEBUI_PORT = '7875'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PATH = "$root\ffmpeg\bin;$root\node;$root\ollama;$env:PATH"
# Use the bundled interpreter directly: venv console EXEs embed the original install path.
$pythonDir = Get-ChildItem -LiteralPath (Join-Path $root 'python') -Directory |
    Where-Object { $_.Name -match '^cpython-3\.12\.' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'python.exe')) } |
    Select-Object -First 1
if (-not $pythonDir) { throw 'Bundled Python is missing. Setup must finish first.' }
$pythonExe = Join-Path $pythonDir.FullName 'python.exe'
$env:PYTHONPATH = Join-Path $root 'venv\Lib\site-packages'
$env:LLM_PROVIDER = 'ollama'
$env:LOCAL_LLM_URL = 'http://127.0.0.1:11435/api/chat'
$env:LOCAL_LLM_MODEL = 'qwen2.5:1.5b'
$env:LLM_MODEL = 'qwen2.5:1.5b'
$ownedServer = $null
try {
    if ($Mode -ne 'doctor') {
        try { $null = Invoke-RestMethod 'http://127.0.0.1:11435/api/tags' -TimeoutSec 2 }
        catch {
            $ollamaExe = Join-Path $root 'ollama\ollama.exe'
            if (-not (Test-Path -LiteralPath $ollamaExe)) { throw 'Portable Ollama is missing.' }
            $ownedServer = Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -WorkingDirectory $root -RedirectStandardOutput "$root\logs\ollama-out.log" -RedirectStandardError "$root\logs\ollama-error.log"
            $ready = $false
            for ($i=0; $i -lt 30; $i++) {
                Start-Sleep -Milliseconds 500
                try { $null = Invoke-RestMethod 'http://127.0.0.1:11435/api/tags' -TimeoutSec 1; $ready=$true; break } catch {}
            }
            if (-not $ready) { throw 'Ollama did not start. See logs\ollama-error.log.' }
        }
    }
    switch ($Mode) {
        'doctor' { & $pythonExe (Join-Path $root 'tools/portable-check.py') }
        'cli' { & $pythonExe -m shortsflow.cli @CliArgs }
        default { & $pythonExe -m shortsflow.cli webui --open }
    }
    $taskExit = $LASTEXITCODE
} finally {
    if ($ownedServer -and -not $ownedServer.HasExited) { Stop-Process -Id $ownedServer.Id -ErrorAction SilentlyContinue }
}
exit $taskExit









