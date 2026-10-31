# OPT-IN only: persistent FastAPI server starts on interactive Windows logon.
# Preview mode makes NO changes. This does not authorize any Facebook publications.
param([switch]$Install,[switch]$Remove)
$ErrorActionPreference="Stop"
$name="Evydencia Facebook - Servidor no Logon"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($Install -and $Remove) { throw "INVALID_FLAGS" }
if ($Remove) {
    $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
    Write-Host "SERVER_LOGON_TASK_REMOVED: server and browser profiles untouched"
    exit 0
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host ("PREVIEW: start FastAPI at interactive logon for current Windows user (no FB post).")
if (-not $Install) { exit 0 }
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
    throw "TASK_ALREADY_EXISTS"
}
$python=Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "PYTHON_VENV_MISSING" }
$script=Join-Path $PSScriptRoot "start_existing_server.ps1"
if (-not (Test-Path $script)) { throw "STARTER_MISSING" }
$ps=(Get-Command powershell.exe -ErrorAction Stop).Source
$action=New-ScheduledTaskAction -Execute $ps -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$script+'" -OpenBrowser') -WorkingDirectory $root
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable:$false -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun:$false -RestartCount 0
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Write-Host "SERVER_LOGON_TASK_INSTALLED: existing login session required; NO Facebook publication enabled"
