# FASE 9 — Windows 11: operação resiliente, diagnóstico e execução Antigravity

Estado: código publicado em PR #9 (Draft), incremental à PR #8. NÃO é homologação do desktop Windows.
Última revisão arquitetural: 31/10/2026. Não fazer merge/main sem fechar gates.

## Revisão forense — cadeia completa

1. `Task Scheduler` usa conta Windows com LogonType Interactive, agenda de horários e política IgnoreNew; este mecanismo não cria sessão de desktop quando usuário está desconectado.
2. `scripts/tick_observed.py` atribui run_id UUID, grava TICK_START/TICK_END ou TICK_EXCEPTION com fsync; fornece EVYD_FORENSIC_RUN_ID a scripts/daily_tick.py e o restaura.
3. `scripts/daily_tick.py` valida configuração + bytes do conteúdo (SHA256), expira atrasos, confere /health e sessão, e grava TICK_RESULT vinculando run_id a job_id antes de sair. Em execuções reais, o multipart inclui run_id e job_id.
4. `app/main.py` valida run_id UUID, recebe job_id e grava ambos em REQUEST_ACCEPTED durável; mantém lock de publicação para Playwright. Nenhum token/cookie/legenda vai ao audit trail.
5. `app/browser.py` roda Playwright em ThreadPoolExecutor(max_workers=1) e perfil persistente isolado por conta; mantém marcador SUBMIT_INTENT antes do clique; falha ou timeout pós-clique é incerto, não sucesso.
6. `app/daily_queue.py` usa SQLite WAL e BEGIN IMMEDIATE, claim conservador NEEDS_REVIEW e migração de jobs para jobs_v2 não destrutiva.
7. `scripts/collect_windows_diagnostics.ps1` capta estado, LastTaskResult, LastRunTime, NextRunTime, NumberOfMissedRuns, execução/concorrência e eventos filtrados sem mensagens brutas.
8. `scripts/start_existing_server.ps1` reinicia SOMENTE se porta 8108 não tiver serviço; nunca mata processos, nunca instala dependências, não modifica perfis Chrome; logs de subprocesso com nomes únicos.
9. `scripts/install_server_logon.ps1` (OPT-IN) registra tarefa separada AtLogOn para usuário interativo. `scripts/run_server_logon.ps1` grava SERVER_LOGON_START/END/FAILED em data/diagnostics/server-logon.jsonl. Startup pode abrir o navegador já autenticado sem publicar.
10. `scripts/export_forensics.py` junta SQLite, operações, ticks, eventos de logon e Task Scheduler; `scripts/validate_forensic_report.py` restringe schema; `scripts/run_forensic_sync.ps1` recusa publicar um snapshot com falha de coleta/SQLite faltando.
11. `reports/forensic/YYYY-MM-DD.json` é retrato SANITIZADO da operação local, e NÃO uma prova de publicação visível no Facebook.

## Matriz de riscos e política de recuperação

| Falha | Detectável por | Ação correta |
| --- | --- | --- |
| Windows suspenso / usuário desconectado | missed_runs, ausência de tick, LastRunTime, event IDs | não fazer catch-up automático; revalidar sessão |
| Outra tarefa em execução IgnoreNew | Task Scheduler e ausência de TICK_START | registrar disparo perdido, não duplicar |
| Servidor indisponível ou revisão divergente | SERVER_NOT_READY / STALE_SERVER | investigar servidor; nunca matar processo desconhecido |
| Chrome deslogado / perfil em uso | ACCOUNT_NOT_READY / erro abertura | revisão humana do login, sem credencial no script |
| Alteração de mídia após planejamento | CONFIG_OR_MEDIA_CHANGED | bloquear antes de claim; nunca trocar mídia silenciosamente |
| Crash após claim, requisição ou clique | NEEDS_REVIEW, TICK_RESULT, SUBMIT_INTENT | NÃO repetir; conferir manualmente a postagem |
| Post em análise ou processamento | PENDING_REVIEW / VIDEO_PROCESSING | preservar tentativa e aguardar confirmação |
| Erro de coleta Windows | EVENT_LOG_* / TASK_QUERY_* | relatório sinaliza coleta incompleta |
| Exportação/push falhou | FORENSIC_COLLECTION_INCOMPLETE / GIT_UPLOAD_FAILED | manter logs brutos locais e tentar apenas sync forense |
| Conteúdo externo não comprovado | SUBMITTED_UNVERIFIED | NÃO liberar avanço autônomo sem verificação independente |

**Limite de capacidade real:** 4 slots × 3 grupos = 12 ocorrências/dia é capacidade de planejamento, não entrega comprovada. Se primeira postagem resultar NEEDS_REVIEW, as próximas são bloqueadas. Não remover a proteção para obter volume. O grupo deve permitir a frequência e a conta deve ter permissão real.

## Microsoft e Playwright — fundamentos oficiais

- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
- https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-logontype-principaltype-element
- https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-multipleinstances
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/get-scheduledtaskinfo
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent
- https://playwright.dev/python/docs/library
- https://playwright.dev/python/docs/api/class-browsertype

Por padrão o Agendador pode não iniciar tarefas na bateria ou interrompê-las ao tirar o notebook da tomada. A agenda de postagem declara AllowStartIfOnBatteries/DontStopIfGoingOnBatteries, RestartCount=0, StartWhenAvailable=false, WakeToRun=false e MultipleInstances=IgnoreNew. LogonType=Interactive exige sessão interativa; não interpretar como serviço Windows.

## Passos objetivos — Antigravity no Windows 11

0. Confirmar `git status --short`, branch, `git rev-parse HEAD`, arquivo data/daily.json, servidor /health e contas. NÃO reset, merge, wipe, force-push ou novo envio real.
1. Validar sintaxe: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_powershell_syntax.ps1`.
2. Rodar `python -m compileall -q app scripts run.py`, `python -m pytest -q`, `python scripts/doctor.py --offline`, `python scripts/verify_scope_safety.py --offline`.
3. Backup da base REAL: `python scripts/backup_forensics.py` antes de qualquer migração (não modificar a base para testar).
4. Conferir `python scripts/daily_tick.py` em preview e simulações offline. `--execute` NÃO é permitido antes de autorização operacional e permalink do canário.
5. Conferir preflight `powershell -File scripts/install_server_logon.ps1` (SEM -Install). Opcionalmente validar `powershell -File scripts/start_existing_server.ps1` com servidor parado e perfil local preservado, sem publicar. Habilitar `-Install` somente se o operador aprovar startup no login.
6. Rodar `powershell -File scripts/collect_windows_diagnostics.ps1`; registrar Task Scheduler real e qualquer erro de coleta.
7. Fazer teste SEM PUBLICAR `python scripts/tick_observed.py` (não passar --execute): validar run_id, TICK_RESULT, TICK_END e journal JSONL. Não fazer isso durante operação incerta.
8. `python scripts/export_forensics.py`, `python scripts/validate_forensic_report.py reports/forensic/YYYY-MM-DD.json`; verificar sanitização.
9. `powershell -File scripts/publish_forensic_report.ps1` em preview. Somente enviar `-Commit -Push` após revisar e autorizar o conteúdo sanitizado.
10. Conferir `powershell -File scripts/install_windows_scheduler.ps1` SEM -Install (preview). Instalar SOMENTE após quatro grupos reais autorizados, configuração da agenda, conferência de repetição, health e canário.
11. Simular Task Scheduler ignorando nova instância, usuário deslogado, servidor divergente, suspensão, duas instâncias, mídias alteradas, crash após claim, falha de banco, falha de sync e porta 8108 ocupada. Cada falha precisa ter código de erro inequívoco.
12. Entregar matriz PASS/FAIL/NÃO TESTADO com IDs e horários sanitizados. Se falta log, marcar gap, não inventar evidência.

## Entrega e segurança

Repo GitHub está PÚBLICO. Não enviar logs completos do browser, HAR, sessões, cookies, tokens, HTML, prints de mensagens privadas ou caminhos de mídia. Manter evidência bruta exclusivamente em data/ e backups privados. Remote snapshot serve para investigação, não substitui dados locais.

Próxima fase inevitável para autonomia contínua: verificador externo legítimo e confiável que confirme grupo + conta + legenda/mídia + publicação no feed + permalink. Nunca auto-resolver NEEDS_REVIEW com base no simples fechamento do compositor ou em POST_UI_CLOSED_UNVERIFIED.

## Revisão de segurança da telemetria publicada (31/10)

O repositório GitHub é público. `scripts/export_forensics.py` cria uma chave de 256 bits em `data/diagnostics/forensic-identity.key` no primeiro uso, sem comitá-la. Nos relatórios reais, IDs de conta, grupo, criativo e legenda recebem HMAC-SHA256 truncado; também se pseudonimiza o `job_id` mantendo 32 hex para preservar a correlação entre jobs, operações, eventos e ticks. Os IDs locais originais permanecem apenas em data/SQLite/operations.jsonl. A chave entra somente no backup LOCAL e deve ser preservada para manter as pseudonimizações estáveis; sem chave válida a exportação falha fechada.

**Windows crítico:** Python `os.open` deve incluir `os.O_BINARY` para escrita de chave ou JSONL em binário; sem isso o modo texto da CRT pode transformar bytes. A suíte de CI Windows cobre geração de chave, redaction, corrupção e consistência de vínculos; NÃO publicar chave, dados pessoais ou logs brutos.

Referência Python: https://docs.python.org/3/library/os.html#os.open
