$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3 -m venv .venv }
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha na instalação das dependências.' }
Write-Host 'Acesse http://127.0.0.1:8108'
Start-Process 'http://127.0.0.1:8108'
& $python run.py
