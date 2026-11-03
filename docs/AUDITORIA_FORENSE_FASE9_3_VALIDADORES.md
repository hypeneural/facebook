# Auditoria forense Fase 9.3 — governança, continuidade e validadores

**Data:** 02/11/2026 · **Repo:** `hypeneural/facebook` · **PR:** #9 (Draft, baseada na #8; `main` preservada).

## Evidência real vs homologação

- Os snapshots `reports/forensic/2026-11-01.json` e `2026-11-02.json` exibem `PLAN_EMPTY`, `task_exists=false`, `server_logon_task_exists=false`, `forensic_sync_task_exists=false` e `EVENT_LOG_DISABLED`. Têm timestamp de exportação recente, mas seus últimos `TICK_START/END` remontam a 31/10. **Gerar relatório recente NÃO comprova execução recente do Agendador.**
- A PR #9 segue em Draft sobre PR #8; a `main` não possui a pilha de fases 3–9. Não há tarefa de publicação instalada nem prova de reboot físico ou permalinks de novos posts nas evidências consultadas.
- O JSONL histórico registra `SERVER_LOGON_FAILED` em 31/10, seguido de sessões START/END bem-sucedidas. Não classificar o conjunto como 100% sem erros, nem inferir que a tarefa de logon foi instalada.
- Relatório sanitizado é pseudonimizado por HMAC local e mantém IDs/horários para correlação. Não equivale a anonimização absoluta. A chave e os logs originais permanecem em `data/`.

## P0/P1 diagnosticados e resolvidos nesta rodada

| Prioridade | Lacuna | Correção | Evidência exigida |
|---|---|---|---|
| P0 | Snapshot novo com execução antiga passava como saudável | `scripts/validate_operational_readiness.py` distingue frescor do relatório, último tick e prontidão | testes `tests/test_operational_readiness.py` |
| P1 | Journal JSONL descartava linhas corrompidas silenciosamente | exportador informa `*_JOURNAL_INVALID_LINES`; truncamento da cauda informa `*_JOURNAL_TAIL_TRUNCATED` | `tests/test_journal_integrity.py` |
| P1 | Cauda do journal começando exatamente num limite de linha podia descartar linha válida | checagem do byte anterior para ignorar apenas a linha parcial | regressão de boundary |
| P1 | Não havia comando único para validar fase 9 sem publicar | `scripts/run_phase9_validation.ps1` tem gates nomeados e opções independentes | sintaxe PowerShell no CI + execução local |
| P1 | Saída integral do pytest podia ir para Git acidentalmente | `-FullTests` grava transcript do pytest SOMENTE em `data/diagnostics/validation/`; resumo só com códigos de gate | teste real Windows |
| P1 | Documentos repetidos dificultam encontrar fonte de verdade | novo documento no índice e habilidade do Antigravity, sem mover arquivos legados nem quebrar links | revisão de documentação |

## Validadores preparados

- **CI e estático:** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_powershell_syntax.ps1` e `python -m pytest -q`.
- **Comando padrão seguro:** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/run_phase9_validation.ps1` — verifica Python, revisão Git, plano SQLite existente e sintaxe PS1. NÃO executa post, migra banco, instala tarefa, faz push ou abre Chrome.
- **Bateria completa local:** adicionar `-FullTests`. O log detalhado fica sob `data/diagnostics/validation/` (ignorado pelo Git).
- **Diagnóstico desktop:** adicionar `-ProbeWindows` após login interativo; verifica /health, build, sessão e plano. `BLOCKED` é falha de prontidão, não justificativa para remover travas.
- **Exportação consentida:** adicionar `-Export` para coletar Windows, gerar o snapshot sanitizado local, validar schema + prontidão. Não faz commit/push. A chave HMAC local é criada se ausente e fica em `data/`.
- **Verificação de arquivo específico:** `python scripts/validate_operational_readiness.py reports/forensic/YYYY-MM-DD.json`, que retorna 0 apenas para diagnósticos internamente completos, 3 para bloqueios/alertas e 2 para entrada inválida. Mesmo retorno 0 **não autoriza postagem**.
- **Arquivo histórico:** `python scripts/validate_operational_readiness.py reports/forensic/YYYY-MM-DD.json --historical`, sem exigir disponibilidade atual da máquina para validar um snapshot arquivado.

Códigos exemplares: `SNAPSHOT_STALE`, `NO_RECENT_TICK`, `TASK_WITHOUT_RECENT_TICK`, `SERVER_LOGON_TASK_NOT_INSTALLED`, `PLAN_CONFIG_DRIFT`, `COLLECTION_PARTIAL`, `EVENT_LOG_UNAVAILABLE`, `TICK_RUN_INCOMPLETE`, `PENDING_PUBLICATION_REVIEW`. Todos sem exibir nomes, URLs, cookies ou caminhos de mídia.

## Microsoft / Playwright — fronteiras operacionais

1. O Task Scheduler com principal `Interactive` exige usuário Windows conectado; não fornece desktop antes do login.
2. `IgnoreNew` não forma fila nem recupera gatilho ignorado. `StartWhenAvailable=false` não tenta executar horários perdidos. O agendamento 0,+5,+15 é só revalidação pré-claim durante janela; `NEEDS_REVIEW` proíbe reenvio.
3. Notebook suspenso não publica sem wake/login; respeitar política energética. Watchdog servidor não executa publicações.
4. Playwright `launch_persistent_context` não deve compartilhar `user_data_dir` com segunda instância nem usar perfil padrão Chrome.
5. A Fase 10 continua necessária para demonstrar grupo, autor, mídia/legenda, permalinks e eventual moderação, com verificador somente leitura antes de qualquer mutação de estado.

Fontes:
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset
- https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-multipleinstances
- https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable
- https://playwright.dev/python/docs/api/class-browsertype

## Ordem cirúrgica para o Antigravity

1. Inspecionar Git e criar backup `python scripts/backup_forensics.py` antes de qualquer alteração local. Não reset, merge, dump ao Git ou limpar perfil Chrome.
2. Rodar `run_phase9_validation.ps1` padrão e registrar gates. Se BLOCKED, não instalar publicador.
3. Rodar `run_phase9_validation.ps1 -FullTests -ProbeWindows`, reproduzir falhas de rede, de reboot e de journal somente em ambiente isolado. Salvar logs locais.
4. Rodar `run_phase9_validation.ps1 -Export` com revisão do snapshot ANTES de qualquer push. Se parcial, registrar o código; não prometer autonomia.
5. Instalação de `server_logon`, watchdog e sync somente mediante autorização, seguida de reboot real controlado e doctor. Não criar agenda de Facebook enquanto Fase 10 for NO-GO.
6. Publicação no grupo ou conciliação externa real exige autorização de canário; `SUBMITTED_UNVERIFIED` / `NEEDS_REVIEW` permanecem bloqueados.
7. Entregar tabela PASS/FAIL/NÃO TESTADO com revisão Git, build, evento/tick, indicação de instalação de tarefas e códigos dos problemas. Atualizar PR #9 Draft; sem merge em `main` nesta rodada.

**Parecer:** GO para validar código e observabilidade; NO-GO para afirmar reinício automático, novos posts reais, ou autonomia total sem evidência local específica.
