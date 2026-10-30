# Diagnóstico Windows 11: apenas IDs de eventos, estado e resultado da tarefa.
# NUNCA registrar stdout de processos, propriedades de sessão, mensagens de eventos ou credenciais.
param([int]$Hours=48)
$ErrorActionPreference="Stop"
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$data=Join-Path $root "data\diagnostics"
New-Item -ItemType Directory -Force -Path $data | Out-Null
$taskName="Evydencia Facebook - Agenda Auditavel"
$result=[ordered]@{
  schema="facebook.win11.v1"
  collected_at_utc=[DateTimeOffset]::UtcNow.ToString("o")
  task=@{exists=$false;state="Unknown";last_result_code=$null}
  recent_event_ids=@()
  errors=@()
}
try {
  $task=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($null -ne $task) {
    $info=Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
    $result.task=@{
      exists=$true;state=[string]$task.State;
      last_result_code=[string]$info.LastTaskResult
    }
  }
} catch {
  $result.errors+=("TASK_QUERY_"+$_.Exception.GetType().Name)
}
try {
  $since=(Get-Date).AddHours(-[Math]::Abs($Hours))
  $events=Get-WinEvent -FilterHashtable @{
    LogName="Microsoft-Windows-TaskScheduler/Operational"; StartTime=$since
  } -MaxEvents 300 -ErrorAction Stop
  # O filtro examina Message localmente, mas jamais a exporta ou registra.
  $filtered=@($events | Where-Object { $_.Message -and $_.Message.Contains($taskName) } | Select-Object -First 100)
  $result.recent_event_ids=@($filtered | ForEach-Object { [int]$_.Id })
  $result.recent_events=@($filtered | ForEach-Object {
    @{ event_id=[int]$_.Id; at_utc=$_.TimeCreated.ToUniversalTime().ToString("o") }
  })
} catch {
  $result.errors+=("EVENT_LOG_"+$_.Exception.GetType().Name)
}
$dest=Join-Path $data "windows.json"
$temp=$dest+".tmp"
$result | ConvertTo-Json -Depth 5 | Set-Content -Path $temp -Encoding UTF8
Move-Item -Force $temp $dest
Write-Host "WINDOWS_DIAGNOSTICS_SAVED: eventos e estado, sem mensagens pessoais."
