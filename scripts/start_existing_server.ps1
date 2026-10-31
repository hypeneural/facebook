# Start only the installed FastAPI server at interactive logon.
# Does NOT install Python, alter browser profiles, publish to Facebook, or kill processes.
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python=Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "PYTHON_VENV_MISSING" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "GIT_MISSING" }
$revision=(& git -C $root rev-parse --short=12 HEAD)
if ($LASTEXITCODE -ne 0 -or -not $revision) { throw "GIT_REVISION_UNKNOWN" }
$revision=("$revision").Trim()
function Health {
    try { return Invoke-RestMethod -Uri "http://127.0.0.1:8108/health" -TimeoutSec 2 }
    catch { return $null }
}
$already=Health
if ($null -ne $already) {
    if ($already.ok -ne $true -or $already.build_revision -ne $revision) {
        throw "STALE_OR_FOREIGN_SERVER: do not kill/restart another process"
    }
    Write-Host "SERVER_ALREADY_READY"
    exit 0
}
# Probe whether another process occupies the port but does not offer our health endpoint.
$tcp=New-Object System.Net.Sockets.TcpClient
try {
    $attempt=$tcp.BeginConnect("127.0.0.1",8108,$null,$null)
    if ($attempt.AsyncWaitHandle.WaitOne(500)) {
        try { $tcp.EndConnect($attempt); throw "PORT_8108_OCCUPIED_UNKNOWN_SERVICE" }
        catch [System.Net.Sockets.SocketException] { }
    }
} finally { $tcp.Close() }
$logs=Join-Path $root "data\diagnostics\server"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$run=[DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")+"-"+[guid]::NewGuid().ToString("N").Substring(0,8)
$stdout=Join-Path $logs ($run+".stdout.log")
$stderr=Join-Path $logs ($run+".stderr.log")
$process=Start-Process -FilePath $python -ArgumentList @("run.py") -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
for ($i=0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    if ($process.HasExited) { throw "SERVER_PROCESS_EXITED: inspect local diagnostics/server logs" }
    $health=Health
    if ($null -ne $health) {
        if ($health.ok -ne $true -or $health.build_revision -ne $revision) {
            throw "SERVER_VERSION_MISMATCH: inspect local diagnostics/server logs"
        }
        Write-Host ("SERVER_STARTED_PID="+$process.Id)
        exit 0
    }
}
throw "SERVER_HEALTH_TIMEOUT: inspect local diagnostics/server logs"
