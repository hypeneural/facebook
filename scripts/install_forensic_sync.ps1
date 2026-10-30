# Opt-in: diagnosticos sanitizados em horarios predefinidos. Nao posta no Facebook.
param([switch]$Install,[switch]$Remove)
$ErrorActionPreference="Stop"
$name="Evydencia Facebook - Sync Forense"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($Install -and $Remove) { throw "INVALID_FLAGS" }
if ($Remove) {
  $existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($existing) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
  Write-Host "Tarefa removida, historico preservado."
  exit 0
}
Write-Host "PREVIEW de snapshots: 09:30, 12:30, 18:30, 20:30, 23:30 (horario do Windows)."
if (-not $Install) { exit 0 }
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "TASK_EXISTS" }
$br=[TimeZoneInfo]::FindSystemTimeZoneById("E. South America Standard Time")
if ([TimeZoneInfo]::Local.GetUtcOffset([DateTime]::UtcNow) -ne $br.GetUtcOffset([DateTime]::UtcNow)) {
 throw "TIMEZONE_MISMATCH"
}
$script=Join-Path $PSScriptRoot "run_forensic_sync.ps1"
$ps=(Get-Command powershell.exe -ErrorAction Stop).Source
$action=New-ScheduledTaskAction -Execute $ps -Argument ('-NoProfile -NonInteractive -File "'+$script+'"') -WorkingDirectory $root
$triggers=@()
foreach ($clock in @("09:30","12:30","18:30","20:30","23:30")) {
  $p=$clock.Split(':')
  $at=(Get-Date).Date.AddHours([int]$p[0]).AddMinutes([int]$p[1])
  $triggers+=New-ScheduledTaskTrigger -Daily -At $at
}
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable:$false -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings -Principal $principal | Out-Null
Write-Host "Tarefa criada; somente reports/forensic sanitizados serao versionados."
