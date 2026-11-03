$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py=Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "PYTHON_VENV_MISSING" }
try {
 & (Join-Path $PSScriptRoot "collect_windows_diagnostics.ps1")
 if (-not $?) { throw "WINDOWS_DIAGNOSTICS_FAILED" }
 & $py (Join-Path $PSScriptRoot "export_forensics.py")
 if ($LASTEXITCODE -ne 0) { throw "EXPORT_FAILED" }
 # Fail closed: an empty/corrupt or partially collected DB must not look like zero jobs.
 $reportPath=Join-Path $root ("reports\\forensic\\"+(Get-Date -Format "yyyy-MM-dd")+".json")
 if (-not (Test-Path $reportPath)) { throw "FORENSIC_REPORT_MISSING" }
 $report=Get-Content -Raw -Encoding UTF8 $reportPath | ConvertFrom-Json
 # A partial sanitized report is valuable evidence; publish it and flag partial status.
 $partial=(@($report.collection_errors | Where-Object { $_ }).Count -gt 0)
 if ($null -ne $report.windows -and @($report.windows.collection_errors | Where-Object { $_ }).Count -gt 0) {
     $partial=$true
 }
 if (-not (Test-Path (Join-Path $root "data\\daily-queue.sqlite"))) { throw "SQLITE_QUEUE_MISSING" }
 if (-not $report.build_revision) { throw "BUILD_REVISION_MISSING" }
 & (Join-Path $PSScriptRoot "publish_forensic_report.ps1") -Commit -Push
 if (-not $?) { throw "GIT_UPLOAD_FAILED" }
 if ($partial) {
     Write-Host "FORENSIC_SYNC_PARTIAL: uploaded with explicit diagnostic errors"
     exit 4
 }
 Write-Host "FORENSIC_SYNC_COMPLETED"
} catch {
 Write-Host ("FORENSIC_SYNC_FAILED_"+$_.Exception.GetType().Name)
 exit 3
}
