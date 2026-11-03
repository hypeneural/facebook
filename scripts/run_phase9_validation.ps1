# Phase 9 one-command validation for Antigravity on Windows 11.
# DEFAULT: no posts, no SQLite migrations, no Task Scheduler installation, no Git changes.
# -ProbeWindows checks current local service/session; -Export explicitly writes
# sanitized diagnostics; -FullTests executes the offline pytest suite.
param([switch]$FullTests,[switch]$ProbeWindows,[switch]$Export)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python=Join-Path $root ".venv\Scripts\python.exe"
$steps=New-Object 'System.Collections.Generic.List[object]'
function Add-Gate([string]$gate,[string]$status,[string]$code) {
    $steps.Add([ordered]@{gate=$gate;status=$status;code=$code})
}
if (-not (Test-Path $python)) {
    Add-Gate "PYTHON" "FAIL" "PYTHON_VENV_MISSING"
} else {
    Add-Gate "PYTHON" "PASS" "PYTHON_VENV_PRESENT"
}
try {
    $rev=(& git -C $root rev-parse --short=12 HEAD)
    if ($LASTEXITCODE -ne 0 -or "$rev" -notmatch '^[0-9a-f]{12}$') { throw "INVALID_GIT_REVISION" }
    Add-Gate "GIT" "PASS" "REVISION_RESOLVED"
} catch {
    Add-Gate "GIT" "FAIL" "REVISION_UNAVAILABLE"
}
# Do NOT run any Python script when the venv is missing.
if (Test-Path $python) {
    try {
        $planOut=@(& $python (Join-Path $PSScriptRoot "inspect_daily_plan.py"))
        $planExit=$LASTEXITCODE
        if ($planExit -eq 0) {
            $plan=($planOut -join "") | ConvertFrom-Json
            Add-Gate "PLAN" "PASS" ([string]$plan.state)
        } elseif ($planExit -eq 3) {
            Add-Gate "PLAN" "BLOCKED" "PLAN_CONFIG_DRIFT"
        } else {
            Add-Gate "PLAN" "BLOCKED" "PLAN_INSPECTION_FAILED"
        }
    } catch {
        Add-Gate "PLAN" "FAIL" "PLAN_PARSE_FAILED"
    }
    if ($FullTests) {
        try {
            Push-Location $root
            try { & $python -m pytest -q | Out-Null; $code=$LASTEXITCODE }
            finally { Pop-Location }
            if ($code -eq 0) { Add-Gate "PYTEST" "PASS" "OFFLINE_TESTS_PASSED" }
            else { Add-Gate "PYTEST" "FAIL" "OFFLINE_TESTS_FAILED" }
        } catch { Add-Gate "PYTEST" "FAIL" "OFFLINE_TESTS_ERROR" }
    }
}
try {
    & (Join-Path $PSScriptRoot "check_powershell_syntax.ps1") | Out-Null
    if ($?) { Add-Gate "POWERSHELL" "PASS" "SYNTAX_OK" }
    else { Add-Gate "POWERSHELL" "FAIL" "SYNTAX_FAILED" }
} catch { Add-Gate "POWERSHELL" "FAIL" "SYNTAX_CHECK_ERROR" }
if ($ProbeWindows) {
    try {
        $diag=@(& (Join-Path $PSScriptRoot "doctor_windows_reboot.ps1"))
        $code=$LASTEXITCODE
        if ($code -eq 0) { Add-Gate "WINDOWS" "PASS" "SUPERVISED_DESKTOP_READY" }
        elseif ($code -eq 3) { Add-Gate "WINDOWS" "BLOCKED" "WINDOWS_READINESS_INCOMPLETE" }
        else { Add-Gate "WINDOWS" "FAIL" "WINDOWS_DOCTOR_FAILED" }
    } catch { Add-Gate "WINDOWS" "FAIL" "WINDOWS_DOCTOR_ERROR" }
}
if ($Export -and (Test-Path $python)) {
    try {
        & (Join-Path $PSScriptRoot "collect_windows_diagnostics.ps1") | Out-Null
        & $python (Join-Path $PSScriptRoot "export_forensics.py") | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "EXPORT_FAILED" }
        $date=(Get-Date -Format "yyyy-MM-dd")
        $target=Join-Path $root ("reports\forensic\"+$date+".json")
        $readiness=@(& $python (Join-Path $PSScriptRoot "validate_operational_readiness.py") $target)
        $exitCode=$LASTEXITCODE
        if ($exitCode -eq 0) { Add-Gate "FORENSICS" "PASS" "DIAGNOSTICS_OK" }
        elseif ($exitCode -eq 3) { Add-Gate "FORENSICS" "BLOCKED" "READINESS_NOT_PROVEN" }
        else { Add-Gate "FORENSICS" "FAIL" "REPORT_OR_READINESS_INVALID" }
    } catch { Add-Gate "FORENSICS" "FAIL" "EXPORT_OR_VALIDATION_FAILED" }
}
$all=@($steps.ToArray())
$failed=@($all | Where-Object { $_.status -eq "FAIL" }).Count
$blocked=@($all | Where-Object { $_.status -eq "BLOCKED" }).Count
$summary=[ordered]@{
    schema="facebook.phase9-check.v1"
    at_utc=[DateTimeOffset]::UtcNow.ToString("o")
    stages=$all
    failed=$failed
    blocked=$blocked
    result=if ($failed -gt 0) {"FAIL"} elseif ($blocked -gt 0) {"BLOCKED"} else {"PASS"}
    facebook_publication_attempted=$false
    facebook_publication_verified=$false
}
$summary | ConvertTo-Json -Depth 6 -Compress
if ($failed -gt 0) { exit 2 }
if ($blocked -gt 0) { exit 3 }
exit 0
