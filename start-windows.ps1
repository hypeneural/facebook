param([switch]$CheckOnly, [switch]$NoOpen)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-Location $PSScriptRoot

function Stage([string]$code, [string]$message) { Write-Host "MVP [$code] $message" }
function Ready {
    try { $r = Invoke-RestMethod -Uri "http://127.0.0.1:8108/health" -TimeoutSec 2 }
    catch { return $false }
    if ($r.ok -ne $true) { return $false }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "REVISION_UNKNOWN: git ausente." }
    $expected = (& git rev-parse --short=12 HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $expected) { throw "REVISION_UNKNOWN: nao foi possivel verificar checkout." }
    if ($r.build_revision -ne "$expected".Trim()) {
        throw "STALE_SERVER: PID $($r.pid), servidor $($r.build_revision), checkout $expected, busy=$($r.busy). Antigravity: confira se ha upload em andamento e reinicie SOMENTE o servidor deste projeto com seguranca. Nao mate processos alheios."
    }
    return $true
}

if (-not $CheckOnly -and (Ready)) {
    Stage "PASS" "Servidor local existente ja responde."
    if (-not $NoOpen) { Start-Process "http://127.0.0.1:8108/" }
    exit 0
}
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $launcher = $null
    $launchArgs = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -c "import sys; assert sys.version_info >= (3,10)" 2>$null
        if ($LASTEXITCODE -eq 0) { $launcher = "py"; $launchArgs = @("-3") }
    }
    if (-not $launcher -and (Get-Command python -ErrorAction SilentlyContinue)) {
        & python -c "import sys; assert sys.version_info >= (3,10)" 2>$null
        if ($LASTEXITCODE -eq 0) { $launcher = "python" }
    }
    if (-not $launcher) { throw "PYTHON_MISSING: Antigravity deve instalar Python 3.12 oficial e executar este script novamente." }
    Stage "SETUP" "Criando ambiente Python."
    & $launcher @launchArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "VENV_FAILED: falha na criacao do ambiente." }
}
$reqHash = (Get-FileHash "requirements.txt" -Algorithm SHA256).Hash
$stamp = Join-Path $PSScriptRoot ".venv\requirements.sha256"
$cached = if (Test-Path $stamp) { (Get-Content $stamp -Raw).Trim() } else { "" }
if ($cached -ne $reqHash) {
    Stage "SETUP" "Instalando dependencias apenas se alteradas."
    & $python -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "PIP_FAILED: falha na instalacao das dependencias." }
    Set-Content -Path $stamp -Value $reqHash -Encoding ascii
}
& $python scripts/doctor.py --offline
if ($LASTEXITCODE -ne 0) { throw "DOCTOR_FAILED: verifique o diagnostico acima." }
if ($CheckOnly) { Stage "PASS" "Preflight offline. Nenhum navegador aberto."; exit 0 }

$chrome = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$([Environment]::GetFolderPath('ProgramFilesX86'))\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) {
    Stage "SETUP" "Chrome nao detectado. Instalando Chromium oficial Playwright."
    & $python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "BROWSER_MISSING: Chromium nao foi instalado." }
}
New-Item -ItemType Directory -Path "data" -Force | Out-Null
if (-not (Ready)) {
    Stage "START" "Iniciando servidor na porta 8108."
    $p = Start-Process -FilePath $python -ArgumentList @("run.py") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "data\server-stdout.log" -RedirectStandardError "data\server-stderr.log"
    $ok = $false
    for ($i=0; $i -lt 40; $i++) {
        if (Ready) { $ok = $true; break }
        if ($p.HasExited) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ok) { throw "SERVER_START_FAILED: consulte data/server-stderr.log." }
    $p.Id | Set-Content -Path "data\server.pid"
}
Stage "PASS" "Painel pronto: http://127.0.0.1:8108/"
if (-not $NoOpen) { Start-Process "http://127.0.0.1:8108/" }
