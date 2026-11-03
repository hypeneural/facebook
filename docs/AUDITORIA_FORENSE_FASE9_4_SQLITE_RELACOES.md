# Fase 9.4 — auditoria forense de SQLite, relacionamentos e backup (02/11/2026)

## Estado e origem da investigação
Repositório `hypeneural/facebook`, PR #9 **Draft** sobre PR #8 (também Draft). A `main` é anterior às fases 3–9. Busca de issues independentes no repositório: sem issues retornadas no momento da inspeção. Não houve acesso do auditor ao banco local real, reboot físico ou postagem Facebook; o CI é offline.

**Decisão arquitetural:** manter `data/daily-queue.sqlite`, `jobs`, `jobs_v2` e `events` intactos. Não introduzir FKs ou migrations destrutivas num arquivo com registros históricos e `NEEDS_REVIEW` enquanto não houver dump sanitizado de estrutura, backup verificado e homologação Windows.

## Mapa de dados, relações e limites

| Origem | Destino/relação | Invariante atual | Observação |
|---|---|---|---|
| `jobs` (legado) | `jobs_v2` por `id` | migração idempotente `INSERT OR IGNORE` | estados incertos antigos devem permanecer; a migração é feita na inicialização do `DailyQueue` |
| `jobs_v2` | `events` por `events.job_id = jobs_v2.id` | relação lógica no código, **não uma FOREIGN KEY declarada** | validar órfãos com anti-join; `PRAGMA foreign_key_check` sozinho não detecta esta relação |
| `jobs_v2.operation_id` | `operations.jsonl` `operation_id` | correlação observacional | não tratar ausência de `operation_id` após crash como licença para retry |
| `jobs_v2` | `daily.json` por conta, grupo, horário, IDs criativo/legenda | `manifest_sha256` protege conteúdo | config local pode mudar; plano do mesmo dia não deve ser sobrescrito |
| `ticks.jsonl` | `jobs_v2.id`, `operations.jsonl` | `run_id → job_id → operation_id` | os logs podem ser truncados em snapshots, os arquivos completos ficam locais |

O SQLite mantém `UNIQUE(day,slot,group_id)` em `jobs_v2`, enquanto a tabela legada só permitia `UNIQUE(day,group_id)`. Sem migração destrutiva, a nova relação é verificada pelo script em modo `?mode=ro` e `PRAGMA query_only=ON`.

### Diagnóstico read-only criado

`python scripts/audit_sqlite_relations.py`

Verifica:
- `PRAGMA integrity_check(1)` e `PRAGMA foreign_key_check` para constraints já declaradas.
- Presença de `jobs`, `jobs_v2`, `events`.
- Jobs legados ainda não copiados para a tabela v2.
- Eventos órfãos da fila v2.
- Reutilização de `operation_id` em jobs distintos.
- Estados inválidos e pendências `NEEDS_REVIEW`.
- Somente códigos fechados e contagens, **sem IDs, clientes, mídia, configuração ou texto**.

Códigos bloqueantes: `SQLITE_SCHEMA_INCOMPLETE`, `LEGACY_JOB_NOT_MIGRATED`, `ORPHAN_JOB_EVENTS`, `OPERATION_ID_REUSED`, `SQLITE_INTEGRITY_CHECK_FAILED`, `SQLITE_FOREIGN_KEY_CHECK_FAILED`. Pendências de revisão retornam `PARTIAL`, e a execução operacional continua bloqueada até conciliação. Nunca reparar automaticamente duplicações, importar historicamente ou mudar estados neste diagnóstico.

### Cobertura e verificação de backup

Antes, `scripts/backup_forensics.py` guardava apenas SQLite e journals, excluindo `data/daily.json` e `data/groups.json`. Isso criava um backup forense incapaz de reconstruir o contexto editorial da fila.

Agora esses dois arquivos são copiados exclusivamente para `data/backups/`, com SHA-256, tamanho e recusa de symlinks para arquivos suplementares. O backup transacional do banco continua usando `sqlite3.backup()`. Não copia Chrome/cookies/perfil, nem envia dados ao Git.

Novo verificador:
`python scripts/verify_backup_forensics.py <caminho_local_do_backup>`

Verifica allowlist de nomes, SHA-256, tamanho, integridade SQL completa e as FKs declaradas. Somente códigos (sem caminhos/valores) são exibidos. **É validação não destrutiva, não restauração**. A recuperação completa da sessão autenticada depende da configuração local do Chrome e do login do operador; não confundir com recuperação de banco.

### Validador unificado do Antigravity

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/run_phase9_validation.ps1 -FullTests -ProbeWindows -Export`

Agora inclui gate `SQLITE` independente. Mantenha os logs de pytest em `data/diagnostics/validation/` e o snapshot público exclusivamente sanitizado. Quando o banco não existe ou tem relacionamentos inconsistentes, retornar `BLOCKED` sem abrir o editor ou disparar publicações.

### Plano de homologação e pontos ainda sem evidência

1. Git branch/HEAD e diff de `main`, PR #8, PR #9. Preservar `data/`, navegador e trabalhos atuais.
2. Com autorização do operador para escrita de backup local, `python scripts/backup_forensics.py`. Pegar caminho do diretório criado em `data/backups/`.
3. `python scripts/verify_backup_forensics.py <backup_dir>`: PASS e hashes iguais. Não restaurar automaticamente.
4. `python scripts/audit_sqlite_relations.py`: PASS ou registrar códigos reais. Se órfãos/legados/duplicados, preservar original e criar relatório de investigação local sem dados no Git público.
5. `run_phase9_validation.ps1 -FullTests -ProbeWindows` e `-Export` com revisão do snapshot.
6. Reinício físico, instalação de tarefas Windows e envio real **NÃO EXECUTADOS REMOTAMENTE**; testar apenas com consentimento no Windows e confirmar `/health`, sessão, Task Scheduler e relação fila/operador.
7. Fase 10: verificador independente read-only de permalink, grupo, conta, conteúdo e moderação. Sem ele, `NEEDS_REVIEW` permanece NO-GO para autonomia.

## Documentação oficial usada na revisão

- SQLite PRAGMA: https://www.sqlite.org/pragma.html (integrity_check / foreign_key_check / query_only)
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html (transações, backup)
- Microsoft Task Scheduler: https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-multipleinstances
- Microsoft StartWhenAvailable: https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable
- Playwright persistent context: https://playwright.dev/python/docs/api/class-browsertype

**Parecer:** GO para estrutura de validadores, backups locais verificados e investigação de dados; NO-GO para alegar prontidão de postagem contínua sem reboot real, tarefa instalada, Event Log operacional e Fase 10 com evidência externa.
