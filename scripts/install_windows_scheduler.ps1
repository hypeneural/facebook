# OPT-IN: por padrão nao instala e nem executa publicacoes.
param([switch]$Install,[switch]$Remove)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$name="Evydencia Facebook - Agenda Auditavel"
$cfgPath=Join-Path $root "data\daily.json"
$python=Join-Path $root ".venv\Scripts\python.exe"
$runner=Join-Path $root "scripts\daily_tick.py"
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
if (-not $Install) { Write-Host "PREVIEW: nenhuma tarefa criada."; exit 0 }
if ($cfg.enabled -ne $true -or $cfg.allow_unattended -ne $true) {
    throw "EXECUTION_NOT_AUTHORIZED: habilitar apenas apos homologacao."
}
if (-not (Test-Path $python)) { throw "PYTHON_VENV_MISSING" }
# Task Scheduler usa o fuso configurado no Windows; não converter horários silenciosamente.
$windowsZone=[TimeZoneInfo]::Local
$brazilZone=[TimeZoneInfo]::FindSystemTimeZoneById("E. South America Standard Time")
if ($windowsZone.GetUtcOffset([DateTime]::UtcNow) -ne $brazilZone.GetUtcOffset([DateTime]::UtcNow)) {
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
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable:$false
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $triggers -Settings $settings -Principal $principal | Out-Null
Write-Host "Tarefa instalada. Requer usuario logado, servidor local e Chrome autenticado."
