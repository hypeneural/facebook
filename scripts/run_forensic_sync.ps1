$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py=Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "PYTHON_VENV_MISSING" }
try {
 & (Join-Path $PSScriptRoot "collect_windows_diagnostics.ps1")
 if (-not $?) { throw "WINDOWS_DIAGNOSTICS_FAILED" }
 & $py (Join-Path $PSScriptRoot "export_forensics.py")
 if ($LASTEXITCODE -ne 0) { throw "EXPORT_FAILED" }
 & (Join-Path $PSScriptRoot "publish_forensic_report.ps1") -Commit -Push
 if (-not $?) { throw "GIT_UPLOAD_FAILED" }
 Write-Host "FORENSIC_SYNC_COMPLETED"
} catch {
 Write-Host ("FORENSIC_SYNC_FAILED_"+$_.Exception.GetType().Name)
 exit 3
}
