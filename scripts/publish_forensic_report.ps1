# Publica SOMENTE relatório previamente sanitizado e validado pelo exportador.
# Sem -Commit não altera Git. Sem -Push não faz network. Nunca git add -A.
param(
    [string]$Date=(Get-Date -Format "yyyy-MM-dd"),
    [switch]$Commit,
    [switch]$Push
)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$target=Join-Path $root ("reports\forensic\"+$Date+".json")
if ($Push -and -not $Commit) { throw "PUSH_REQUIRES_COMMIT" }
if ($Date -notmatch '^\d{4}-\d{2}-\d{2}$') { throw "INVALID_DATE" }
if (-not (Test-Path $target)) { throw "REPORT_NOT_FOUND: execute export_forensics.py" }
if ((Get-Item $target).Length -gt 4MB) { throw "REPORT_TOO_LARGE" }
$data=Get-Content -Raw -Encoding UTF8 $target | ConvertFrom-Json
if ($data.schema -ne "facebook.forensic.v1" -or $data.provenance -ne "local_sanitized_export_not_external_facebook_proof") {
    throw "UNEXPECTED_REPORT_SCHEMA"
}
# Confirmar que o arquivo não contém chaves brutas sensíveis nem paths locais.
$raw=Get-Content -Raw -Encoding UTF8 $target
if ($raw -match '"(cookie|password|token|caption|filepath|filename|path|html|dom|url|secret|text)"\s*:') {
    throw "SENSITIVE_FIELD_BLOCKED"
}
if (-not $Commit) {
    Write-Host "PREVIEW: $target validado. Para versionar, use -Commit. Para enviar, -Commit -Push."
    exit 0
}
Push-Location $root
try {
    $branch=(git branch --show-current).Trim()
    if ($branch -ne "audit/forensic-observability-windows-20261030") {
        throw "WRONG_BRANCH"
    }
    # Adiciona SOMENTE reports/forensic/<data>.json. Nunca stage data/ ou config local.
    $relative="reports/forensic/$Date.json"
    git add -- $relative
    if ($LASTEXITCODE -ne 0) { throw "GIT_ADD_FAILED" }
    $staged=@(git diff --cached --name-only)
    if (@($staged | Where-Object { $_ -ne $relative }).Count -gt 0) {
        git reset -- $relative | Out-Null
        throw "UNRELATED_STAGED_FILES: não registrar outros arquivos no commit"
    }
    git commit -m "chore(forensics): snapshot sanitizado $Date"
    if ($LASTEXITCODE -ne 0) { throw "GIT_COMMIT_FAILED" }
    if ($Push) {
        git push origin $branch
        if ($LASTEXITCODE -ne 0) { throw "GIT_PUSH_FAILED" }
    }
} finally { Pop-Location }
