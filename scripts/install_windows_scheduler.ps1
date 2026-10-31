# OPT-IN: por padrão nao instala e nem executa publicacoes.
param([switch]$Install,[switch]$Remove)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$name="Evydencia Facebook - Agenda Auditavel"
$cfgPath=Join-Path $root "data\daily.json"
$python=Join-Path $root ".venv\Scripts\python.exe"
$runner=Join-Path $root "scripts\tick_observed.py"
if ($Install -and $Remove) { throw "Escolha apenas Install ou Remove." }
if ($Remove) {
    $existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing) { Unregister-ScheduledTask -TaskName $name -Confirm:$false }
    Write-Host "Tarefa removida. Historico e sessoes mantidos."
    exit 0
}
if (-not (Test-Path $cfgPath)) {
    Write-Host "Crie data\daily.json a partir de config\daily.example.json"
    if ($Install) { throw "CONFIG_MISSING" }
    exit 0
}
$cfg=Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Horarios: $($cfg.slots -join ', '); grupos por horario: $($cfg.groups_per_slot)"
$plannedMax=[int]$cfg.slots.Count * [int]$cfg.groups_per_slot
Write-Host "Maximo teorico: $plannedMax publicacoes por dia; grupos cadastrados: $($cfg.groups.Count)"
Write-Host "Limite configurado por grupo/dia: $($cfg.max_posts_per_group_per_day)"
if ($cfg.timezone -ne "America/Sao_Paulo") { throw "TIMEZONE_CONFIG_MISMATCH" }
# IMPORTANT: previews must inspect the actual frozen SQLite day, not just the JSON.
# No database creation/migration and no clicks in this read-only inspection.
if (-not (Test-Path $python)) { throw "PYTHON_VENV_MISSING" }
$inspection=& $python (Join-Path $root "scripts\inspect_daily_plan.py") --config $cfgPath --db (Join-Path $root "data\daily-queue.sqlite")
$inspectorCode=$LASTEXITCODE
if ($inspection) { Write-Host ("PLANO_DIAGNOSTICO: "+(@($inspection) -join " ")) }
if ($inspectorCode -ne 0) { throw "PLAN_INSPECTION_FAILED_OR_DRIFT: examine the dated plan without deleting any jobs." }
if (-not $Install) { Write-Host "PREVIEW: nenhuma tarefa criada."; exit 0 }
if ($cfg.enabled -ne $true -or $cfg.allow_unattended -ne $true) {
    throw "EXECUTION_NOT_AUTHORIZED: habilitar apenas apos homologacao."
}
if (-not (Test-Path $python)) { throw "PYTHON_VENV_MISSING" }
if (-not (Test-Path $runner)) { throw "RUNNER_MISSING" }
# Run pure config validation; do not create/modify SQLite while installing a task.
Push-Location $root
try {
    & $python -c 'import json,sys; from app.daily_queue import validate_config; validate_config(json.load(open(sys.argv[1],encoding="utf-8-sig")))' $cfgPath
    if ($LASTEXITCODE -ne 0) { throw "CONFIG_VALIDATION_FAILED" }
} finally { Pop-Location }
# A healthy server at the same revision is a prerequisite for approval, never kill another process.
$expected=(& git -C $root rev-parse --short=12 HEAD)
if ($LASTEXITCODE -ne 0 -or -not $expected) { throw "GIT_REVISION_UNKNOWN" }
try {
    $health=Invoke-RestMethod -Uri "http://127.0.0.1:8108/health" -TimeoutSec 4
} catch { throw "SERVER_NOT_READY: inicie o servidor manualmente e confira a sessão." }
if ($health.ok -ne $true -or $health.busy -eq $true) { throw "SERVER_BUSY_OR_NOT_READY" }
if ($health.build_revision -ne "$expected".Trim()) { throw "STALE_SERVER" }
# Task Scheduler usa o fuso configurado no Windows; não converter horários silenciosamente.
$windowsZone=[TimeZoneInfo]::Local
$brazilZone=[TimeZoneInfo]::FindSystemTimeZoneById("E. South America Standard Time")
if ($windowsZone.Id -ne $brazilZone.Id -or $windowsZone.GetUtcOffset([DateTime]::UtcNow) -ne $brazilZone.GetUtcOffset([DateTime]::UtcNow)) {
    throw "WINDOWS_TIMEZONE_MISMATCH: configure o fuso do Windows para horário de Brasília antes de instalar."
}
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw "TASK_ALREADY_EXISTS" }
$triggers=@()
foreach ($slot in $cfg.slots) {
    if ($slot -notmatch '^\d{2}:\d{2}$') { throw "INVALID_CLOCK" }
    $parts=$slot.Split(':')
    for ($i=0; $i -lt [int]$cfg.groups_per_slot; $i++) {
        $at=(Get-Date).Date.AddHours([int]$parts[0]).AddMinutes([int]$parts[1]+10*$i)
        if ($at.Date -ne (Get-Date).Date) { throw "SLOT_OVERFLOWS_DAY" }
        $triggers+=New-ScheduledTaskTrigger -Daily -At $at
    }
}
$action=New-ScheduledTaskAction -Execute $python -Argument ('"' + $runner + '" --execute') -WorkingDirectory $root
# Notebook: Windows defaults may skip on battery or stop on AC loss.
# No late catch-up, no wake and NO task-level retry of uncertain Facebook operations.
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable:$false -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun:$false -RestartCount 0
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings -Principal $principal | Out-Null
$confirmed=Get-ScheduledTask -TaskName $name -ErrorAction Stop
if ($confirmed.Settings.MultipleInstances -ne "IgnoreNew" -or $confirmed.Principal.LogonType -ne "Interactive") {
    throw "TASK_REGISTERED_BUT_SETTINGS_MISMATCH: inspecionar antes de executar."
}
Write-Host "Tarefa instalada. Requer usuario logado, servidor local e Chrome autenticado; bateria permitida, sem auto-retry ou catch-up."
