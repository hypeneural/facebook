---
name: verificar-mvp
description: Valida offline a estrutura Python, dependências e API do Facebook Grupos MVP sem abrir Chrome, acessar Facebook ou publicar; usar antes e depois de correções no código.
---

# /verificar-mvp — somente testes sem efeitos externos
Na raiz do projeto, executar:
1. powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1 -CheckOnly
2. .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt (se pytest ausente).
3. .\.venv\Scripts\python.exe scripts/doctor.py --offline
4. .\.venv\Scripts\python.exe -m compileall -q app run.py scripts
5. .\.venv\Scripts\python.exe -m pytest -q

Se falhar: guardar comando, traceback e arquivo exatos. Corrigir somente o necessário, testar afetado e uma suíte final. Não iniciar navegador ou fazer postagem nesta habilidade.
