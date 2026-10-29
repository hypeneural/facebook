# Workflow /mvp-local — Antigravity
1. Clonar https://github.com/hypeneural/facebook.git no Windows.
2. Executar powershell -ExecutionPolicy Bypass -File .\start-windows.ps1
3. Se Chromium não existir: .\.venv\Scripts\python.exe -m playwright install chromium
4. Abrir http://127.0.0.1:8108 e clicar Abrir Chrome.
5. Login MANUAL na janela do Chrome, clicar Conferir login.
6. Abrir um grupo autorizado de teste. Inserir legenda e UMA foto de teste (sem dados privados).
7. Com aprovação do operador, Publicar uma vez. Verificar visualmente grupo e link do post, ou aprovação pendente.
8. Se houver erro de seletor: observar interface PT-BR real e alterar apenas app/browser.py.
9. Rodar .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
10. Rodar .\.venv\Scripts\python.exe -m compileall app run.py
11. Rodar .\.venv\Scripts\python.exe -m pytest -q
12. Reportar PASS/FAIL por etapa, evidência real e eventual link. Nunca inventar publicação.
FORA DO MVP: recorrência, múltiplos grupos, múltiplas contas, envio em massa.
