# Índice operacional — Facebook Groups (31/10/2026)

**Fonte de verdade:** scripts e testes em Git + SQLite em `data/` do Windows. Este arquivo resume a navegação e o estado, não substitui os dossiês.

## Branches e ordem segura

| Etapa | PR | Descrição | Estado |
|---|---|---|---|
| base | main | app original, histórico de testes | publicada sem Fases 7–9 |
| 3–6 | #3–#6 | media/upload, watchdog UI, troca de grupos, editor Lexical | branches Draft/homologações reportadas |
| 7 | #7 | SQLite seguro, uma tentativa, NEEDS_REVIEW | Draft na pilha |
| 8 | #8 | slots, quatro grupos, jobs_v2, plano imutável | Draft; base da PR #9 |
| 9 | #9 | Windows, telemetria, snapshots, drift, reboot, rede | Draft; sem merge |
| 10 | proposta | reconciliação externa de post real | NÃO IMPLEMENTADA |

Não fazer merge direto da #9 na main sem conferir dependências e ordem de revisão de branches. Sem `git reset --hard` em `data/` nem migração destrutiva do SQLite. Não arquivar PRs como concluídas sem verificar em qual base estão.

## Documentação canônica (sem duplicar)

- **Runbook e arquitetura:** `docs/OPERACAO_RESILIENTE_WINDOWS11_FACEBOOK_FASE9.md`
- **Auditoria independente de rede/reboot:** `docs/AUDITORIA_INDEPENDENTE_FASE9_2_REDE_REBOOT.md`
- **Relatório local Antigravity:** `docs/RELATORIO_HOMOLOGACAO_FASE9_1_REBOOT_E_PLANO.md`
- **Revisão forense anterior:** `docs/AUDITORIA_FORENSE_WINDOWS_FASE9.md`
- **Proposta Fase 10:** `docs/PROPOSTA_CONCILIACAO_EXTERNA_FASE10.md`
- **Habilidade Antigravity:** `.agents/skills/fase9-logs-windows/SKILL.md`
- **Snapshots públicos:** `reports/forensic/YYYY-MM-DD.json`, *sanitizados* e explicitamente não comprovam postagem real
- **Logs e perfis locais:** `data/` (nunca versionar cookies, chaves de HMAC, nomes, mídia, DOM, backups ou dumps)

## Executáveis e funções

| Arquivo | Responsabilidade |
|---|---|
| `app/daily_queue.py` | planejamento, SQLite WAL, idempotência, estado incerto e diagnóstico de drift |
| `scripts/inspect_daily_plan.py` | conferência read-only da configuração vs jobs congelados |
| `scripts/tick_observed.py` | entrada do Task Scheduler, run_id, início/fim, snapshot |
| `scripts/daily_tick.py` | preflight, TLS externo antes do claim, mídia, envio no máximo uma vez |
| `scripts/start_existing_server.ps1` | FastAPI e Chrome na sessão existente |
| `scripts/run_server_logon.ps1` | entrada serializada via mutex, trilha START/END/FAILED |
| `scripts/install_server_logon.ps1` | instalação opt-in da tarefa no login |
| `scripts/install_server_watchdog.ps1` | instalação opt-in do monitor do servidor, sem publicar |
| `scripts/install_windows_scheduler.ps1` | agenda de posts opt-in, não instalar enquanto NO-GO |
| `scripts/collect_windows_diagnostics.ps1` | eventos e estado do Windows, sem mensagens sensíveis |
| `scripts/doctor_windows_reboot.ps1` | diagnóstico read-only após reboot/login |
| `scripts/export_forensics.py` | exportação sanitizada e chave HMAC local |
| `scripts/run_forensic_sync.ps1` | publicação de snapshots com status completo/parcial |

## Gates para mudar estado

**GO observabilidade (parcial):** CI verde, logs locais duráveis, report validado, erros de Event Log expostos com fidelidade.

**GO recuperação após reboot:** só após tarefa de login instalada com consentimento, reboot físico, mesmo usuário interativo, `/health` no HEAD, sessão Chrome, log START+END, plano correto e auditoria sem duplicidade.

**GO publicação periódica:** somente após a conciliação Fase 10 demonstrar post visível/permalink com prova suficiente e autorização do gestor. O Scheduler de postagem deve continuar ausente/desativado enquanto isso.

**P0 permanente:** nunca reexecutar um job depois de `SUBMIT_INTENT` ou HTTP incerto; `NEEDS_REVIEW` é a trava intencional de segurança.
