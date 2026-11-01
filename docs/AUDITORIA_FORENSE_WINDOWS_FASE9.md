# FASE 9 — AUDITORIA FORENSE Windows 11 e telemetria auditável

Data 30/10/2026. Base: PR #8 head ed722f925c67213d31b530c21c4650bb1e01bea8. PR #9 é incremental em Draft. NÃO alterar main ou perfis locais.

## Evidências e diagnóstico do código
- O aplicativo já possui app/telemetry.py: operações JSONL estruturadas, submit-intents duráveis, estágios, status e erros classificados. app/daily_queue.py mantém jobs_v2 e eventos SQLite transacionais. A UI consulta operações e agenda.
- Faltava vincular um job ao request no servidor antes de receber a resposta do HTTP: se o Windows crashar após transmitir arquivos, o SQLite guarda NEEDS_REVIEW mas operation_id pode nunca chegar ao executor. A PR #9 envia job_id de 32 hex pelo multipart e o servidor registra job_id no REQUEST_ACCEPTED.
- Faltava uma trilha separada para cada ativação real do Task Scheduler, com PID, duração, código de saída e crash. scripts/tick_observed.py escreve data/diagnostics/ticks.jsonl com os.write+fsync e captura erro apenas por classe.
- Faltava capturar o estado da tarefa Windows e os eventos do log Microsoft-Windows-TaskScheduler/Operational. scripts/collect_windows_diagnostics.ps1 coleta tarefa, estado/exit e IDs de eventos, SEM mensagem completa.
- Faltava pacote único para auditoria remota: scripts/export_forensics.py produz reports/forensic/YYYY-MM-DD.json, com schema facebook.forensic.v1. É um RELATÓRIO SANITIZADO, não cópia de data/.
- Faltava procedimento para enviar o relatório ao GitHub: scripts/publish_forensic_report.ps1 é opt-in, só permite adicionar o JSON específico depois de validar schema e branch. Sem -Commit, preview. -Commit -Push envia exclusivamente esse relatório. scripts/run_forensic_sync.ps1 encadeia coleta, export e envio, e scripts/install_forensic_sync.ps1 oferece agendamento separado opt-in.
- Os logs brutos de operações, histórico, SQLite, ticks e sessões ficam em data/ ignorado por git. RAW cookies/tokens/senhas/legendas/DOM, caminhos de mídia, HAR, captura completa de console e fotos NÃO são publicados em GitHub. Isso evita que um incidente de acesso ao repositório comprometa a conta Facebook ou os arquivos pessoais.
- Logs de eventos do Task Scheduler, stdout do Powershell, stack traces e caminhos de usuário podem conter dados sensíveis. NÃO usar Start-Transcript indiscriminadamente; a documentação Microsoft explica que captura todos os comandos e saídas. Preferir códigos de estado enumerados e contexto técnico.
- CI Windows do Github NÃO demonstra Task Scheduler instalado no desktop real. Até Antigravity executar os gates abaixo, marcar cenário Windows real como NÃO TESTADO.

## Padrão de observabilidade
Chaves de correlação: job_id (SQLite; 32 hex), operation_id (UUID do publicador), run_id (UUID de cada tick), hora UTC/horário de Brasília, build_revision SHA12.
Estágios observáveis: TICK_START, REQUEST_ACCEPTED(job_id), FILES_STAGED, GROUP_DESTINATION_VERIFIED, COMPOSER_OPEN, CAPTION_FILLED, MEDIA_PREVIEW_READY, CAPTION_RECHECK_PASSED, PRE_SUBMIT_DESTINATION_RECHECK, SUBMIT_INTENT, SUBMIT_RETURNED, POST_UI_OBSERVED, API_RESPONSE, TICK_END. Em falha: TICK_EXCEPTION, PREFLIGHT_FAILED, POST_UI_CLOSED_UNVERIFIED, NEEDS_REVIEW.
No snapshot remoto: ID de job e operação, hash truncado de conta/grupo/criativo/legenda, bytes, duração, stage, status, error_code; sem conteúdo do texto nem arquivo.
Ao receber POST_UI_CLOSED_UNVERIFIED, continuar NEEDS_REVIEW. Relatório GitHub não comprova postagem no Facebook, apenas identifica a tentativa e seus marcos.

## Procedimento em Windows 11
1. Ler AGENTS.md e skill /fase9-logs-windows, verificar branch, HEAD e alterações locais. Preservar data/ e todas as sessões. NÃO reset/force/merge.
2. Testar: python -m pytest -q; python scripts/doctor.py --offline; python scripts/verify_scope_safety.py --offline; python -m compileall -q app scripts.
3. Atualizar servidor SOMENTE se não houver upload e health busy=false; conferir health.build_revision==git rev-parse --short=12 HEAD.
4. Confirmar que arquivo data/daily.json continua privado, grupos permitidos e opção enabled/allow_unattended não alterada.
5. Criar evento de teste com dados sintéticos, não publicar no Facebook. Validar REQUEST_ACCEPTED com job_id, proteção contra id inválido, TICK_START/TICK_END e exportação do snapshot.
6. PowerShell -File scripts/collect_windows_diagnostics.ps1: confirmar presença/ausência REAL da tarefa existente e Operation log. Se log não puder ser lido, registrar EVENT_LOG_* sem inventar zero eventos.
7. python scripts/export_forensics.py --date YYYY-MM-DD: conferir reports/forensic/YYYY-MM-DD.json, schema, id, timings, contadores, nenhum cookie/caption/path.
8. PowerShell -File scripts/publish_forensic_report.ps1: PREVIEW seguro, sem stage/commit. Com aprovação, -Commit e eventualmente -Commit -Push, sempre na branch audit/forensic-observability-windows-20261030.
9. PowerShell -File scripts/install_forensic_sync.ps1: PREVIEW do sincronizador de diagnósticos. Se autorizado, -Install. Não confundir com scripts/install_windows_scheduler.ps1 (este agenda PUBLICAÇÕES).
10. Conferir em GitHub snapshot sanitizado e se o próprio ChatGPT consegue lê-lo pelo conector.
11. Testar caso servidor sem login, Windows dormindo, tarefa encerrada por timeout, permissão de eventos negada, falha Git push e queda durante envio multipart: logs precisam distinguir cada estado, sem repetir publicação incerta.
12. Não habilitar agenda de postagens antes de confirmar grupos, frequência e canário com permalink; preservar trava NEEDS_REVIEW.

## Limites operacionais oficiais do Windows
- New-ScheduledTaskPrincipal -LogonType Interactive requer usuário em sessão interativa; não é serviço de desktop e não garante automação quando usuário está desconectado.
- MultipleInstances=IgnoreNew ignora nova instância da MESMA tarefa, mas não todas as outras tarefas ou instâncias manuais. SQLite BEGIN IMMEDIATE ainda é obrigatório.
- StartWhenAvailable=false não recupera tarefa perdida após suspensão; é proposital em campanhas que não devem fazer envios fora de horário.
- ExecutionTimeLimit 30 minutos pode interromper envio; estado e markers duráveis precisam ser revisados. Não configurar RestartCount >0 para o publicador.
- Notebook em suspensão/hibernação pode perder disparos. Não forçar WakeToRun sem necessidade e autorização. Não tentar bypass de Facebook/CAPTCHA.

## Docs Microsoft oficiais
- https://learn.microsoft.com/en-us/windows/win32/taskschd/about-the-task-scheduler
- https://learn.microsoft.com/en-us/windows/win32/TaskSchd/taskschedulerschema-multipleinstancespolicy-settingstype-element
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.host/start-transcript

## GO/NO-GO
GO: implementar/reportar diagnósticos com CI e homologação Windows.
NO-GO: entregar logs brutos irrestritos ao GitHub, instalar tarefas sem autorização, iniciar campanha autônoma que depende da confirmação externa de post ainda não implementada.

## Revisão independente adicional — 30/10/2026 (ChatGPT, GitHub)
- [CONFIRMADO NO CÓDIGO] Exportador `summarize` limita ticks a 3000 registros; validador antigo limitava qualquer coleção a 2500. Corrigida regra por coleção: jobs=500, job_events=2500, operations=2500, ticks=3000, com regressão para 2800 ticks. Antes desta correção, `-Commit -Push` recusaria um relatório válido de alto volume.
- [CONFIRMADO NO CÓDIGO] Consulta de Windows antes trazia apenas estado e último resultado, sem horários da última/próxima execução, perda de disparos e política de concorrência. Coletor agora lê os campos não sensíveis `last_run_utc`, `next_run_utc`, `missed_runs`, `multiple_instances`, `logon_type` e `execution_limit_minutes`, com allowlist no export e validação. Se a leitura de propriedades for incompatível, registrar TASK_QUERY_* e tratar cenário como não homologado.
- [CONFIRMADO NO CÓDIGO] Coletor limita os eventos recentes a 300 eventos e os filtrados a 100; agora anota `event_scan_count` e `event_scan_truncated` para não declarar falsamente que não houve erros fora da janela. Observação: o filtro de eventos tem dependência da mensagem localizada do Windows, devendo ser testado no desktop real.
- [LIMITE DE PROVA] CI Windows GitHub não tem a sessão interativa, os quatro grupos e os eventos da máquina Windows 11 do operador. Nenhuma prova de postagem real/permalink nesta PR. A sincronização de snapshots não significa que o ChatGPT possua acesso aos logs brutos ignorados por Git.
- [P0 PENDENTE] Retornar `SUBMITTED_UNVERIFIED` não pode ser convertido em `VERIFIED_EXTERNALLY` sem prova de URL pública/identidade do post, grupo, conta, mídia e horário. Sem confirmação não há envio seguinte.
- [P1 PENDENTE] Verificar no Windows se `ExecutionTimeLimit` é retornado como TimeSpan ou texto ISO-8601 no PowerShell utilizado; se o cast falhar, corrigir só o coletor, sem mexer na fila.
- [P1 PENDENTE] A trilha `run_id` está em ticks.jsonl; operações não carregam `run_id` no multipart, logo a junção entre tick e job atualmente depende de tempos/eventos. Para correlação perfeita, introduzir `run_id` com validação e propagação ponta a ponta em PR separada com testes.
- [SECURITY] O repositório é público. Jamais subir perfis Chrome, dumps, capturas completas, logs brutos, legendas, cookies, tokens, nomes ou identificadores pessoais. `reports/forensic/` permanece estritamente sanitizado; IDs pseudonimizados não equivalem a anonimização absoluta.
- [OPERACIONAL] Manter backup SQLite local antes de qualquer migração; reler HEAD e `/health` antes de simulações. Não instalar Task Scheduler, não ativar postagens e não executar outro canário nesta revisão.
