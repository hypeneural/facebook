# Read-only proof of Windows reboot recovery. Does not start or post anything.
# Run in the SAME interactive Windows account used by the browser.
param([switch]$RequirePublishingTask)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$components=@(
  @{id="server_logon";name="Evydencia Facebook - Servidor no Logon"},
  @{id="publishing";name="Evydencia Facebook - Agenda Auditavel"},
  @{id="forensic_sync";name="Evydencia Facebook - Sync Forense"}
)
$result=[ordered]@{
    schema="facebook.reboot-check.v1"
    at_utc=[DateTimeOffset]::UtcNow.ToString("o")
    local_timezone_matches=([TimeZoneInfo]::Local.Id -eq "E. South America Standard Time")
    server_healthy=$false
    server_revision_matches=$false
    browser_session_ready=$false
    plan_state="UNKNOWN"
    tasks=@{}
    errors=@()
}
foreach ($part in $components) {
    try {
        $task=Get-ScheduledTask -TaskName $part.name -ErrorAction SilentlyContinue
        $result.tasks[$part.id]=@{
           exists=($null -ne $task)
           state=if ($null -eq $task) { "Unknown" } else { [string]$task.State }
        }
    } catch {
        $result.tasks[$part.id]=@{exists=$false;state="Unknown"}
        $result.errors+=("TASK_QUERY_"+$_.Exception.GetType().Name)
    }
}
try {
    $health=Invoke-RestMethod -Uri "http://127.0.0.1:8108/health" -TimeoutSec 5
    $result.server_healthy=($health.ok -eq $true -and $health.busy -ne $true)
    $expected=(& git -C $root rev-parse --short=12 HEAD)
    if ($LASTEXITCODE -eq 0) {
        $result.server_revision_matches=("$expected".Trim() -eq [string]$health.build_revision)
    }
} catch {
    $result.errors+="SERVER_UNAVAILABLE"
}
if ($result.server_healthy) {
    try {
        $session=Invoke-RestMethod -Uri "http://127.0.0.1:8108/api/session" -TimeoutSec 15
        $result.browser_session_ready=($session.logged_in -eq $true)
    } catch { $result.errors+="SESSION_UNAVAILABLE" }
}
$python=Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $python) {
    $inspection=@(& $python (Join-Path $PSScriptRoot "inspect_daily_plan.py"))
    if ($LASTEXITCODE -eq 0 -and $inspection.Count -gt 0) {
        try {
            $plan=($inspection -join "") | ConvertFrom-Json
            $result.plan_state=[string]$plan.state
        } catch { $result.errors+="PLAN_OUTPUT_INVALID" }
    } else {
        $result.plan_state=if ($LASTEXITCODE -eq 3) {"PLAN_CONFIG_DRIFT"} else {"PLAN_CHECK_FAILED"}
    }
} else {
    $result.errors+="PYTHON_VENV_MISSING"
}
$result.ready_for_supervised_operation=(
    $result.local_timezone_matches -and $result.server_healthy -and
    $result.server_revision_matches -and $result.browser_session_ready -and
    $result.plan_state -in @("PLAN_MATCH","PLAN_EMPTY") -and
    $result.tasks.server_logon.exists -and
    (!$RequirePublishingTask -or $result.tasks.publishing.exists)
)
# No user names, paths, account/group IDs, cookies or page text are emitted.
$json=$result | ConvertTo-Json -Depth 6 -Compress
Write-Output $json
if (-not $result.ready_for_supervised_operation) { exit 3 }
exit 0
