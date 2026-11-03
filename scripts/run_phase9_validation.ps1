# Offline-by-default Phase 9 checks. No posts, migrations, installations or git push.
param([switch]$FullTests,[switch]$ProbeWindows,[switch]$Export)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python=Join-Path $root ".venv\Scripts\python.exe"
$steps=New-Object 'System.Collections.Generic.List[object]'
function Add-Gate([string]$gate,[string]$status,[string]$code) {
    [void]$steps.Add([ordered]@{gate=$gate;status=$status;code=$code})
}
if (Test-Path $python) {
    Add-Gate "PYTHON" "PASS" "PYTHON_VENV_PRESENT"
} else {
    Add-Gate "PYTHON" "FAIL" "PYTHON_VENV_MISSING"
}
try {
    $rev=(& git -C $root rev-parse --short=12 HEAD)
    if ($LASTEXITCODE -ne 0 -or "$rev" -notmatch '^[0-9a-f]{12}$') { throw "BAD_REVISION" }
    Add-Gate "GIT" "PASS" "REVISION_RESOLVED"
} catch { Add-Gate "GIT" "FAIL" "REVISION_UNAVAILABLE" }
if (Test-Path $python) {
    try {
        $planOut=@(& $python (Join-Path $PSScriptRoot "inspect_daily_plan.py"))
        $planExit=$LASTEXITCODE
        if ($planExit -eq 0) {
            $plan=($planOut -join "") | ConvertFrom-Json
            if ($plan.state -eq "PLAN_EMPTY") { Add-Gate "PLAN" "WARN" "PLAN_EMPTY_NO_EXECUTION" }
            else { Add-Gate "PLAN" "PASS" ([string]$plan.state) }
        } elseif ($planExit -eq 3) {
            Add-Gate "PLAN" "BLOCKED" "PLAN_CONFIG_DRIFT"
        } else {
            Add-Gate "PLAN" "BLOCKED" "PLAN_INSPECTION_FAILED"
        }
    } catch { Add-Gate "PLAN" "FAIL" "PLAN_PARSE_FAILED" }
    if ($FullTests) {
        try {
            $localLogs=Join-Path $root "data\diagnostics\validation"
            New-Item -ItemType Directory -Force -Path $localLogs | Out-Null
            $logFile=Join-Path $localLogs ("pytest-"+[DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")+".log")
            Push-Location $root
            try {
                & $python -m pytest -q *> $logFile
                $testExit=$LASTEXITCODE
            } finally { Pop-Location }
            if ($testExit -eq 0) { Add-Gate "PYTEST" "PASS" "OFFLINE_TESTS_PASSED" }
            else { Add-Gate "PYTEST" "FAIL" "OFFLINE_TESTS_FAILED_LOG_LOCAL" }
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
        & (Join-Path $PSScriptRoot "doctor_windows_reboot.ps1") | Out-Null
        $doctorCode=$LASTEXITCODE
        if ($doctorCode -eq 0) { Add-Gate "WINDOWS" "PASS" "SUPERVISED_DESKTOP_READY" }
        elseif ($doctorCode -eq 3) { Add-Gate "WINDOWS" "BLOCKED" "WINDOWS_READINESS_INCOMPLETE" }
        else { Add-Gate "WINDOWS" "FAIL" "WINDOWS_DOCTOR_FAILED" }
    } catch { Add-Gate "WINDOWS" "FAIL" "WINDOWS_DOCTOR_ERROR" }
}
if ($Export -and (Test-Path $python)) {
    try {
        & (Join-Path $PSScriptRoot "collect_windows_diagnostics.ps1") | Out-Null
        & $python (Join-Path $PSScriptRoot "export_forensics.py") | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "EXPORT_FAILED" }
        $reportDate=(Get-Date -Format "yyyy-MM-dd")
        $target=Join-Path $root ("reports\forensic\"+$reportDate+".json")
        $raw=@(& $python (Join-Path $PSScriptRoot "validate_operational_readiness.py") $target)
        $readinessCode=$LASTEXITCODE
        $reason="READINESS_NOT_PROVEN"
        try {
            $parsed=($raw -join "") | ConvertFrom-Json
            $safeCodes=@()
            foreach ($item in (@($parsed.problems)+@($parsed.warnings))) {
                if ($item -is [string] -and $item -match '^[A-Z0-9_]{3,64}$') { $safeCodes+=$item }
            }
            if ($safeCodes.Count -gt 0) { $reason=(@($safeCodes | Sort-Object -Unique) -join ",") }
        } catch {
            $reason="READINESS_RESULT_INVALID"
        }
        if ($readinessCode -eq 0) { Add-Gate "FORENSICS" "PASS" "DIAGNOSTICS_OK" }
        elseif ($readinessCode -eq 3) { Add-Gate "FORENSICS" "BLOCKED" $reason }
        else { Add-Gate "FORENSICS" "FAIL" "REPORT_OR_READINESS_INVALID" }
    } catch { Add-Gate "FORENSICS" "FAIL" "EXPORT_OR_VALIDATION_FAILED" }
}
$all=@($steps.ToArray())
$failed=@($all | Where-Object { $_.status -eq "FAIL" }).Count
$blocked=@($all | Where-Object { $_.status -eq "BLOCKED" }).Count
$warned=@($all | Where-Object { $_.status -eq "WARN" }).Count
$resultStatus=if ($failed -gt 0) {"FAIL"} elseif ($blocked -gt 0) {"BLOCKED"} elseif ($warned -gt 0) {"PARTIAL"} else {"PASS"}
$summary=[ordered]@{
    schema="facebook.phase9-check.v1"
    at_utc=[DateTimeOffset]::UtcNow.ToString("o")
    stages=$all
    failed=$failed
    blocked=$blocked
    warnings=$warned
    result=$resultStatus
    facebook_publication_attempted=$false
    facebook_publication_verified=$false
}
$summary | ConvertTo-Json -Depth 6 -Compress
if ($failed -gt 0) { exit 2 }
if ($blocked -gt 0 -or $warned -gt 0) { exit 3 }
exit 0
