# Fase 7 — Auditoria forense completa e agenda Windows auditável

30/10/2026. Base conferida: PR #6 HEAD bc3b3eb. Esta PR é incremental e Draft.

## Achados confirmados
- scripts/verify_scope_safety.py: overall_pass antigo ignorava ausência do servidor e revisão divergente. CORRIGIDO com health, build, busy e modo --offline separado.
- scripts/check_dialogs.py: falhas Win32 podiam retornar falso ZERO_DIALOGS_FOUND e exit 0. CORRIGIDO: EnumWindows, Abrir/Open e exit 2 em erro/ambiente sem Windows. A varredura não é específica do Chrome.
- scripts/start_default_server.ps1: CreateProcess WinSta0 com Wait-Process criava segundo inicializador sem os gates de start-windows.ps1. CORRIGIDO para wrapper.
- requirements.txt: Python Windows não inclui necessariamente base IANA; tzdata adicionada para America/Sao_Paulo.
- AGENTS.md: restrições antigas da Fase 2 contradiziam a agenda; a autorização da Fase 7 é explícita e independente.
- app/telemetry.py: submit-intents protege uma operação, não repetições em novas requisições. Nova fila persiste chave de dia/grupo em SQLite.
- app/browser.py: o último estado das publicações reais ainda é SUBMITTED_UNVERIFIED. NÃO significa que o Facebook publicou.

## Benchmarks de projetos externos (padrões estudados, código não copiado)
- hthmkt12/flowkit, MIT (agent/db/crud.py, agent/worker/processor.py): claim transacional, lease, fingerprint e sucesso possível sem retry. Base para SQLite e conservação do resultado incerto.
- phantakanxm/facebook-group-autopost, licença não identificada (packages/db/prisma/schema.prisma; apps/worker/src/campaigns/runner.ts): tabelas Campaign/Group/PostLog e cancelamento. NÃO copiar retorno de sucesso após 4 s ou retries genéricos.
- WahuVN/facebook-group-poster, licença não identificada (fb_group_poster.py): erro de publicação ambígua e JSONL; não copiar retry sem evidência de pré-clique.
- thenotoriousmrkrabs/opencli-plugin-fb-autopost, licença não confirmada (group-post.js, src/composer.js): conferir legenda e mídia após anexar, verificação de sessão.
- 0xEnc0der/fbcli, MIT (fbcli/web_actions.py): ideia de permalink, mas fallback de URL de grupo não prova postagem; não usar GraphQL privado.
- ariknih/autopost-facebook-group, MIT (main.py): LOOP_POSTING e repetição curta são inadequados para grupos autorizados e segurança operacional.

## Arquitetura Fase 7
Configuração local ignorada pelo Git: data/daily.json, a partir de config/daily.example.json.
- enabled=false e allow_unattended ausente por padrão; nenhuma postagem/instalação é ativada no GitHub.
- timezone America/Sao_Paulo; slots podem ser 08:00, 10:00, 16:00, 18:00, 22:00.
- Somente grupos explicitamente autorizados pelo operador e pelas regras do grupo.
- Seleção aleatória de grupo/creative/texto é reproduzível por rotation_seed e data; não usa jitter para evadir limites.
- Máximo de 3 grupos por slot, a cada 10 minutos, um grupo por dia por campanha.
- app/daily_queue.py mantém SQLite WAL + índice UNIQUE(day,group_id), INSERT OR IGNORE, BEGIN IMMEDIATE e hash do manifesto.
- Em primeiro claim: NEEDS_REVIEW ANTES de contato HTTP; qualquer perda de rede/reinício mantém estado incerto, nunca auto-retry.
- Tarefas com atraso superior a 20 minutos viram MISSED, sem catch-up cego.
- Alteração do texto/asset após planejamento gera CONFIG_CHANGED antes do clique.
- scripts/daily_tick.py, sem --execute, faz somente planejamento. Com --execute, exige enabled e allow_unattended, servidor build correto, conta local ativa e sessão existente; envia multipart em streaming a FastAPI local em 127.0.0.1:8108.
- Status após chamada API sempre NEEDS_REVIEW até verificação externa por operador. Resolver manualmente via --resolve-id, --resolve-status e --reason.
- Logs de eventos SQLite sem legendas, fotos, paths, tokens ou cookies. Justificativa manual armazenada só como hash.
- scripts/install_windows_scheduler.ps1 não faz nada por padrão. Com -Install e config homologada, cria tarefa Windows interativa do usuário atual para cada slot, sem privilégios SYSTEM.
- O navegador deve permanecer aberto na sessão do Windows; Task Scheduler não transforma um serviço em desktop interativo.

## Matriz de falhas
Servidor indisponível, perfil incorreto, build divergente ou vídeo ativo: WAITING_PREFLIGHT e evento PREFLIGHT_FAILED; pode reavaliar dentro da janela, sem clique.
Computador dormindo além de 20 minutos: MISSED; NÃO redisparar.
Falha/transporte após claim: NEEDS_REVIEW; NÃO repetir.
HTTP 200 + SUBMITTED_UNVERIFIED: NEEDS_REVIEW; NÃO inferir publicado.
Mídia local alterada após plano: CONFIG_CHANGED; impedir emissão.
Apenas verificação externa do operador permite VERIFIED_EXTERNALLY ou SKIPPED; nunca mudar job incerto para PLANNED.

## Gates no Windows antes de GO
1. git status/branch, preservar data/ e sessões; não fazer merge.
2. Python compileall, doctor offline, pytest, verificar escopo --offline, CI PASS.
3. Confirmar 127.0.0.1:8108 health build_revision correspondente a git e login ativo.
4. Construir data/daily.json com grupos autorizados, textos aprovados e arquivos locais. Rodar primeiro com enabled=false.
5. Testar preview via python scripts/daily_tick.py, confirmando slots e conteúdos ID sem publicação.
6. Testar falha Win32, servidor offline, build divergente, conta errada, vídeo pendente, config mudada, mídia ausente, crash após claim, duas instâncias, horário vencido e dia seguinte.
7. Testar envio multipart somente contra mock FastAPI local, jamais usar repetidamente um grupo real.
8. Com autorização explícita: único canário real e prova no feed com mídia íntegra.
9. Verificar que o resultado incerto pausa todos os slots até revisão; isso É esperado.
10. Somente após revisão da arquitetura e autorização, configurar enabled=true e allow_unattended=true e instalar Task Scheduler via PowerShell -Install.
11. Testar login Windows interativo, tarefa sem elevação, hibernação, reinício e logs.

## Limite para produção
O executável de agenda foi desenvolvido, mas ainda NÃO é uma campanha totalmente autônoma por vários dias sem supervisão. Como o atual publicador encerra os posts em SUBMITTED_UNVERIFIED, a fila pausa após a primeira postagem. É intencional: ainda falta comprovação automática de post no feed/permalink, identidade real de publicação e painel de conciliação. Nunca remover essa barreira apenas para aumentar volume.

Documentação oficial:
- https://playwright.dev/python/docs/actionability
- https://learn.microsoft.com/en-us/windows/win32/taskschd/schtasks
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
- Meta Graph API v19: publish_to_groups removida em 22/04/2024.
