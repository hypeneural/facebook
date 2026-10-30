# Compatibilidade com scripts antigos: usar exclusivamente o inicializador auditado.
# Não executar CreateProcess/WinSta0 independente nem manter PID concorrente.
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $root "start-windows.ps1") -NoOpen
if (-not $?) { throw "START_WINDOWS_FAILED" }
