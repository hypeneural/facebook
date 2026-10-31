# Auditoria independente — Fase 9.2: rede, reboot, logs e continuidade

**Data:** 31/10/2026  
**Repositório:** hypeneural/facebook · PR #9 Draft (base PR #8 Draft)  
**Escopo:** revisão independente dos commits do Antigravity `7e23909`, `ee1957c`, relatório local Fase 9.1 e snapshot sanitizado. Nenhuma postagem real, Task Scheduler installation, merge ou execução no desktop foi realizada pelo auditor.

## Prova vs lacuna

| Componente | Evidência concreta | Limite da evidência |
|---|---|---|
| CI Windows | HEAD Antigravity ee1957c PASS | não valida reboot físico ou postagem real |
| SQLite plano | 31/10 PLAN_CONFIG_DRIFT: 1 job às 11:25 vs cinco slots autorizados | configuração só vale em nova data limpa; não replanejar dados já persistidos |
| Distribuição | simulação isolada 01/11: cinco jobs, quatro grupos, cap2 | plano calculado não é publicação confirmada |
| Coleta Event Log | snapshot `windows.event_log_status=DISABLED`, `EVENT_LOG_DISABLED` global e aninhado | desabilitado NÃO implica falta de eventos ou origem de permissões; é necessário inspecionar no Windows |
| Inicialização | snapshot teve `SERVER_LOGON_END`; relatório diz START+END local | BOM UTF-8 na primeira linha podia ocultar START no exportador; corrigido |
| Windows | FastAPI `/health` e sessão autenticada em teste manual | não substitui teste real de reboot com usuário conectado |
| Task Scheduler | logon, watchdog, sync e publicação ausentes no snapshot | instaladores não executados; no-retry preservado |
| Facebook | SUBMITTED_UNVERIFIED em operações históricas | nunca prova postagem visível; Fase 10 pendente |

## Melhorias incrementais aplicadas nesta revisão

1. **Rede pré-claim** — `scripts/daily_tick.py` verifica TCP+TLS certificado de `www.facebook.com:443` somente depois do preflight local e antes de transição irreversível para `NEEDS_REVIEW`. Ausência de conectividade gera `NETWORK_NOT_READY` e mantém o job `PLANNED` até expirar a janela natural de 20 min. Falha DEPOIS do claim permanece `TRANSPORT_OR_PUBLISH_UNCERTAIN` e exige conciliação; nunca retry cego.
2. **Proxy/rede corporativa** — verificação direta TLS pode falhar em ambientes que exigem proxy mesmo quando o navegador usa proxy. É um bloqueio conservador de segurança, não evidência de que o Facebook esteja indisponível. O Antigravity deve comprovar a rota real antes de habilitar publicação. Não adicionar exceção de certificado, fallback sem TLS ou bypass.
3. **Windows JSONL** — escrita `run_server_logon.ps1` agora usa UTF8Encoding(false), sem BOM; `read_jsonl` aceita o histórico com UTF-8 BOM. Regra necessária para que a primeira linha `SERVER_LOGON_START` não seja descartada silenciosamente.
4. **Corrida de inicialização** — mutex nomeado entre as tarefas de logon/watchdog impede ambas de tentarem iniciar o FastAPI usando a mesma porta ao mesmo tempo. A tarefa não encerra Chrome/processos de terceiros.
5. **Erros sem exposição** — log de `TRANSPORT_OR_PUBLISH_UNCERTAIN` preserva a classe da exceção (e não `str(exc)`), mantendo IDs de execução e zero mensagens com caminhos, cookies ou mídia.
6. **Regressões** — novos testes para offline pré-claim, erro depois do claim e sem retry, JSONL Windows BOM e classe sanitizada.
7. **Organização** — este documento consolida os novos gates; não recriar nem duplicar scripts por fase. Apenas `data/` contém configs reais, perfis, backups e chave de HMAC, e essa pasta permanece ignorada pelo Git.

## Requisitos Windows 11 / Playwright

- Microsoft: `InteractiveToken` requer sessão já logada (https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-logontype-principaltype-element).
- Microsoft: `IgnoreNew` ignora um segundo disparo; `StartWhenAvailable` atrasa a tarefa após horário; `AllowStartIfOnBatteries` e `DontStopIfGoingOnBatteries` são explícitos no ScheduledTasks (https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset).
- Microsoft: `Get-WinEvent -ListLog` permite verificar `IsEnabled` no canal TaskScheduler/Operational (https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent).
- Playwright: Chrome não suporta duas instâncias com o mesmo `user_data_dir`; browser profile automatizado deve ser dedicado (https://playwright.dev/python/docs/api/class-browsertype).
- Meta: API de Grupos/`publish_to_groups` foi descontinuada em 22/04/2024 (https://developers.facebook.com/docs/graph-api/changelog/version19.0). Não propor API privada, coleta de credenciais ou evasão de restrições. A navegação pelo navegador real continua frágil e condicionada às regras de cada grupo.

## Procedimento cirúrgico — Antigravity local

**PREPARE (sem publicar):**
1. `git status --short`, verificar PR #9 HEAD, HEAD do servidor, `data/`, permissões locais, perfis e quaisquer modificações não comitadas. Não force-push, reset, rm SQLite ou alterar startup de outros serviços.
2. Backup: `python scripts/backup_forensics.py` e testar leitura do backup (somente leitura).
3. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_powershell_syntax.ps1`, `python -m compileall -q app run.py scripts`, `python -m pytest -q`, `python scripts/doctor.py --offline`.
4. `python scripts/inspect_daily_plan.py` — se PLAN_CONFIG_DRIFT, manter pausa e não reescrever dia corrente; usar `--date 2026-11-01` apenas se essa data estiver limpa e for adequada ao teste.
5. Verificar a rota TLS de forma não publicadora: `python -c "from scripts.daily_tick import probe_facebook_tls; print(probe_facebook_tls())"`. Se falso, checar DNS, proxy, firewall e certificados, sem desativar TLS.
6. `powershell -NoProfile -File scripts/collect_windows_diagnostics.ps1`; se Event Log DISABLED, registrar como PARCIAL; habilitar log só com aprovação e privilégios Windows, sem mudar permissões de outros serviços.
7. `powershell -NoProfile -File scripts/doctor_windows_reboot.ps1` (read-only); verificar usuário interativo, `/health`, build, perfil, fuso, tarefas instaladas. Um resultado `ready=false` nunca é PASS de recuperação.
8. Pré-visualizar instaladores SEM `-Install`: `install_server_logon.ps1`, `install_server_watchdog.ps1`, `install_forensic_sync.ps1`, `install_windows_scheduler.ps1`.

**REBOOT GATE, somente com consentimento do operador:**
9. Se autorizado, instalar APENAS inicialização do servidor e monitor, preservar sessões e realizar reboot real controlado. Após login validar health, Chrome, START+END com mesmo UUID, mutex, plano SQLite, ausência de processos duplicados e snapshots. Reproduzir rede offline ANTES do claim e verificar NETWORK_NOT_READY sem mudança de estado.
10. Reproduzir queda depois de claim em teste simulado: NÃO reenviar, preservar NEEDS_REVIEW e operation_id/run_id; validar exportação e backup sem vazar dados.
11. Publicar snapshot sanitizado na PR após revisão de dados, indicando erros de coleta e sem alterar relatório histórico sem versionamento.
12. Criar matriz PASS/FAIL/NÃO TESTADO com commit, build_revision, id do teste, código, event ID e horários, sem informações de perfil.

**NO-GO:** Postagem autônoma (enabled=false/allow_unattended=false), live canary, Task Scheduler de publicação e PR merge enquanto Fase 10 não comprovar publicação no grupo e permalink. Não alterar flags automaticamente.

## Fase 10 — refinamento necessário

Verificador externo deve ser **somente leitura** inicialmente. Nome aparente de autor, prefixo de legenda, quantidade de thumbnails e janela de 15 minutos são heurísticas e NÃO identificação criptográfica inequívoca de um post. Requerir prova específica com permalink único que pertença ao grupo, conta correta, evidência do conteúdo aprovado e correspondência temporal; caso ambíguo permanece NEEDS_REVIEW. Um post aguardando moderação NÃO é publicado. Só autorizar a transição `VERIFIED_EXTERNALLY` depois de um teste consentido e de validação independente. API pública oficial de Grupos para publicar não existe mais.

## P0 adicional — PREVIEW_ONLY não pode gravar no banco real

A auditoria do código comprovou que `tick(execute=False)` anteriormente chamava `store.plan(cfg,today)` **antes** de verificar a flag de preview. Como os planos diários são imutáveis, um simples teste de preview poderia congelar o dia no SQLite verdadeiro e impedir alterações posteriores. A divergência de 31/10 não prova, sozinha, qual execução original criou o job, mas o bug era material.

**Correção nesta branch:**
- `preview_tick` compara o plano existente em somente leitura e, se não houver plano, simula no SQLite `:memory:` sem conexão com o DB real.
- `daily_tick.main()` não cria nem migra `data/daily-queue.sqlite` em preview; `read_existing_jobs` usa URI SQLite read-only, se o DB existe.
- `execute=True` preserva planejamento transacional e proteção de `NEEDS_REVIEW`.
- Testes `tests/test_preview_readonly.py` verificam zero criação de DB, zero alteração de jobs existentes e drift sem mutações; `test_daily_tick.py` foi ajustado ao contrato de preview verdadeiramente não destrutivo.

**Gate Antigravity:** antes de habilitar qualquer publicação, executar `python scripts/daily_tick.py` sem `--execute` e comparar hash/contagem da base e `jobs_v2` antes/depois; deve ser idêntico. O novo planejamento só pode entrar na base quando o executor autorizado rodar em modo execução, ou durante manutenção explícita e auditável — nunca como efeito de um preview.
