# Entrypoint of the optional Windows logon task; durable metadata only.
# Raw startup exception text, profile paths and browser DOM must stay off Git.
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$path=Join-Path $root "data\diagnostics\server-logon.jsonl"
New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
$runId=[guid]::NewGuid().ToString("D")
$started=[Diagnostics.Stopwatch]::StartNew()
function Emit([string]$stage,[int]$exitCode,[string]$errorClass="") {
    $event=[ordered]@{
        at=[DateTimeOffset]::UtcNow.ToString("o")
        run_id=$runId
        stage=$stage
        exit_code=$exitCode
        duration_ms=[int]$started.ElapsedMilliseconds
    }
    if ($errorClass -match '^[A-Za-z]{2,60}$') { $event.error_class=$errorClass }
    $line=($event | ConvertTo-Json -Compress)
    [System.IO.File]::AppendAllText($path,$line+[Environment]::NewLine,(New-Object System.Text.UTF8Encoding($false)))
}
Emit "SERVER_LOGON_START" 0
try {
    & (Join-Path $PSScriptRoot "start_existing_server.ps1") -OpenBrowser
    if (-not $?) { throw "SERVER_START_FAILED" }
    Emit "SERVER_LOGON_END" 0
    exit 0
} catch {
    Emit "SERVER_LOGON_FAILED" 4 ($_.Exception.GetType().Name)
    Write-Host "SERVER_LOGON_FAILED: inspect local server diagnostics"
    exit 4
}
