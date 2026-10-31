# Optional safe watchdog: if FastAPI died after logon, re-open it on the
# current interactive desktop. It NEVER executes the publishing tick.
param([switch]$Install,[switch]$Remove)
$ErrorActionPreference="Stop"
$name="Evydencia Facebook - Monitor do Servidor"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($Install -and $Remove) { throw "INVALID_FLAGS" }
if ($Remove) {
    $existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
    Write-Host "SERVER_WATCHDOG_REMOVED"
    exit 0
}
Write-Host "PREVIEW: checks the existing FastAPI once an hour at :05, interactive user only; NO Facebook posts."
if (-not $Install) { exit 0 }
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "TASK_ALREADY_EXISTS" }
if (-not (Get-ScheduledTask -TaskName "Evydencia Facebook - Servidor no Logon" -ErrorAction SilentlyContinue)) {
    throw "SERVER_LOGON_TASK_REQUIRED"
}
$runner=Join-Path $PSScriptRoot "run_server_logon.ps1"
if (-not (Test-Path $runner)) { throw "SERVER_RUNNER_MISSING" }
$ps=(Get-Command powershell.exe -ErrorAction Stop).Source
$action=New-ScheduledTaskAction -Execute $ps -Argument ('-NoProfile -NonInteractive -File "'+$runner+'"') -WorkingDirectory $root
# Explicit daily triggers avoid reliance on unsupported combinations of
# -Daily and -RepetitionInterval in Windows PowerShell 5.1.
$triggers=@()
for ($hour=0; $hour -lt 24; $hour++) {
    $at=(Get-Date).Date.AddHours($hour).AddMinutes(5)
    $triggers+=New-ScheduledTaskTrigger -Daily -At $at
}
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable:$false -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun:$false -RestartCount 0
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Principal $principal -Settings $settings | Out-Null
Write-Host "SERVER_WATCHDOG_INSTALLED: restart-check only, no published content"
