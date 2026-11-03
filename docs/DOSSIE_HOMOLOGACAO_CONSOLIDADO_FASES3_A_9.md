# Dossiê de Homologação Consolidado — Fases 3 a 9 (PRs #3, #4, #5, #6, #7 e #9)

**Data de Consolidação:** 31 de Outubro de 2026  
**Repositório:** `hypeneural/facebook`  
**Branch Atual:** `audit/forensic-observability-windows-20261030` (PR #9 Draft)  
**Ambiente:** Windows 11 Pro, Python 3.12.10, PowerShell 5.1, Sessão Interativa `WinSta0\Default`  
**Autor:** Antigravity (Gemini 3.8 Flash)  
**Auditoria Forense Externa:** ChatGPT  

---

## 1. Resumo Executivo das Fases Homologadas

| Fase | PR | Branch | Commit Homologado | Escopo Principal | Status |
|:---:|:---:|:---|:---:|:---|:---:|
| **3** | #3 | `fix/filechooser-media-preflight-forensic-20261030` | `67da3a6` | Upload direto de mídias sem modal `#32770` e prova quantitativa | **PASS** |
| **4** | #4 | `fix/video-posting-state-watchdog-20261030` | `5669c54` | Watchdog de carregamento de vídeo ("Postando") pós-clique | **PASS** |
| **5** | #5 | `fix/group-switch-preflight-resilience-20261030` | `0ff7584` | Troca segura entre grupos e perfis persistentes no Windows | **PASS** |
| **6** | #6 | `fix/lexical-editor-scope-safety-20261030` | `bc3b3eb` | Editor Lexical restrito a `[role="dialog"] [contenteditable="true"]` | **PASS** |
| **7** | #7 | `feat/daily-queue-audit-foundation-20261030` | `084b444` | Fila diária SQLite WAL, hash SHA-256 de manifestos e no-retry | **PASS** |
| **9.0** | #9 | `audit/forensic-observability-windows-20261030` | `6f0f7e7` | Telemetria Windows, `run_id → job_id → operation_id`, HMAC | **PASS** |
| **9.1** | #9 | `audit/forensic-observability-windows-20261030` | `ee1957c` | Diagnóstico de plan drift, doctor de reboot e 160 testes CI | **PASS** |
| **9.2** | #9 | `audit/forensic-observability-windows-20261030` | `82830dd` | Preview zero-write, `probe_facebook_tls`, mutex startup, 169 testes | **PASS** |
| **10** | Prop | — | — | Conciliação externa com permalink e verificação no feed | **PROPOSTA** |

---

## 2. Princípios de Segurança e Travas Permanentes

1. **Preservação de Dados:** A pasta `data/` (perfis Chrome, cookies, banco SQLite, chave privada HMAC e journals) nunca é versionada ou exposta.
2. **Zero Retries Automáticos:** Qualquer incerteza pós-clique (`SUBMIT_INTENT` registrado) ou erro HTTP transacional mantém `NEEDS_REVIEW` e pausa a fila até conferência externa.
3. **Imutabilidade de Planos Diários:** Dias já planejados no SQLite não são alterados ou recalculados automaticamente após mudanças em `data/daily.json`.
4. **Preview Zero-Write:** O modo de visualização simula a distribuição em `:memory:` e não altera um único byte da base de produção.
5. **Fail-Closed em Rede:** Quedas de internet antes do claim emitem `NETWORK_NOT_READY` e preservam a cota do grupo; checkpoints em `0`, `+5` e `+15` minutos permitem nova tentativa apenas do pré-voo dentro da janela de 20 minutos.
6. **Controle de Concorrência:** Mutex nomeado `Local\EvydenciaFacebookServerStartup` impede corridas na inicialização do FastAPI.
7. **Pseudonimização Criptográfica:** Snapshots públicos no GitHub usam hashes HMAC-SHA256 estáveis sem expor URLs, legendas ou nomes de grupos.

---

## 3. Matriz Consolidada da Fase 9 (PR #9)

| ID | Componente / Cenário | Critério de Aceite | Resultado | Evidência Forense |
|:---|:---|:---|:---:|:---|
| **M01** | Bateria Pytest Offline | 169 testes passando no Windows 11 | **PASS** | `169 passed, 1 warning in 8.80s` |
| **M02** | Sintaxe PowerShell | 13 scripts `.ps1` validados sintaticamente | **PASS** | `POWERSHELL_SYNTAX_PASS_COUNT=13` |
| **M03** | Preview Não Destrutivo | SHA-256 do SQLite idêntico antes/depois | **PASS** | Hash `4FA371EB...` inalterado (45056 bytes) |
| **M04** | Sonda TLS Facebook | `probe_facebook_tls` conecta a `www.facebook.com:443` | **PASS** | Respondeu `True` sem bypass de certificado |
| **M05** | Simulações de Falha de Rede | `NETWORK_NOT_READY` pré-claim e `NEEDS_REVIEW` pós | **PASS** | 4 testes aprovados em `test_network_outage_preflight.py` |
| **M06** | Gatilhos Bounded de Agendador | Checkpoints 0,+5,+15 min capped em 48 | **PASS** | `SAFE_TRIGGER_COUNT = 15` (5 slots $\times$ 1 grupo $\le 48$) |
| **M07** | Mutex de Startup Windows | Serialização via mutex nomeado Win32 | **PASS** | `Local\EvydenciaFacebookServerStartup` ativo |
| **M08** | Tolerância a UTF-8 BOM | Pares START/END preservados na exportação | **PASS** | 2 testes aprovados em `test_windows_jsonl_encoding.py` |
| **M09** | Servidor FastAPI no HEAD | PID 15328, `/health` com revisão `82830dd` | **PASS** | `build_revision: "82830dd8d0be"`, `ok: true`, `busy: false` |
| **M10** | Sessão Chrome & Pré-voo Live | `/api/session`, escopo e Win32 dialogs | **PASS** | `logged_in: true` (Anderson Marques), `ZERO_MATCHING_DIALOGS_FOUND` |
| **M11** | Doctor de Reinício Read-Only | `doctor_windows_reboot.ps1` | **PASS** | Servidor, revisão, sessão e timezone OK; drift congelado |
| **M12** | Coleta Diagnóstico Windows 11 | `collect_windows_diagnostics.ps1` | **PASS (PARCIAL)** | Identificado `event_log_status: "DISABLED"` com erro seguro |
| **M13** | Preview dos Instaladores | 4 scripts PowerShell em preview | **PASS** | Zero tarefas criadas; bloqueio fail-closed por drift ativo |
| **M14** | Snapshot Sanitizado Público | `export_forensics.py` + validador | **PASS** | Snapshot validado (`REPORT_SCHEMA_APPROVED`) e commit `6da4db8` |
| **M15** | Reinício Físico do Windows | Reboot da máquina do operador | **NÃO TESTADO** | Mantido sob controle operacional do usuário |
| **M16** | Publicação Real no Facebook | Disparo live de postagem | **NÃO TESTADO** | Proibido nesta fase; nenhuma publicação adicional sem autorização |

---

## 4. Parecer Técnico Final GO / NO-GO

- **GO PARA A FASE 9 (PR #9):** Aprovada no Windows 11 com 169 testes no CI, zero mutações no SQLite em preview, resiliência de rede e conectividade TLS comprovadas, startup com mutex, tolerância a BOM e relatórios sanitizados no GitHub.
- **NO-GO PARA PUBLICAÇÃO AUTÔNOMA DESACOMPANHADA:** As proteções `enabled: false` e `allow_unattended: false` permanecem ativas em `data/daily.json`. A agenda de postagem em background não foi instalada no Windows Task Scheduler. Toda nova publicação exige autorização explícita do operador e a futura homologação da conciliação externa da Fase 10.
