# Fase 8 — Auditoria forense P0 para operação diária no Windows (30/10/2026)

Base examinada: PR #7 no commit beb6c914a2b76af5d4c4737cd892d83116abaaf2.
Nova PR: fix/production-slot-rotation-20261030 (Draft, base PR #7).

## Evidência efetiva do Antigravity (Fase 7)
- pytest 112/112 e CI do commit da PR #7 passaram (offline). Os scripts test_simulations_phase7.py e test_multipart_mock.py usam mocks locais, não Facebook remoto.
- A operação real 627b4aa2-efa7-42e6-916a-24a408ce00aa no Grupo B teve SUBMIT_INTENT e POST_UI_CLOSED_UNVERIFIED. A conciliação posterior gravou VERIFIED_EXTERNALLY por decisão manual. O dossiê não fornece permalink independente para nós verificarmos o post.
- /health com revisão 084b444 não equivale a comprovação da revisão final beb6c91 (que adicionou relatórios e simulações). Validar a revisão exata novamente após atualização.
- Task Scheduler em modo preview: 0 tarefas, logo a agenda recorrente ainda não foi instalada na máquina pelo Antigravity.

## Achados do código pré-Fase 8
P0-01: DailyQueue.plan() mantinha cursor único e UNIQUE(day,group_id). Com 4 grupos, no máximo 4 jobs ao dia, mesmo com 3 grupos por slot × 4 slots. Impede objetivo solicitado.
P0-02: Replanejar com config alterada poderia anexar jobs adicionais ao mesmo dia em algumas estratégias de expansão; a política precisa imutabilidade desde o primeiro plano.
P0-03: Uma migração destrutiva de jobs/SQLite eliminaria rastreabilidade de ocorrências já conciliadas; proibido DELETE/DROP/RESET.
P1-04: A fila SQLite não tinha dashboard de horários, grupos, operações e NEEDS_REVIEW no painel Web.
P1-05: Erro de mídia/manifesto antes do claim não produzia evento padronizado nem código de saída específico do Task Scheduler.
P1-06: O instalador não mostrava volume total de publicações nem verificava o fuso Windows.
P1-07: Auto-dispatch NÃO confirma externo via permalink; sem verificação, as ocorrências param em NEEDS_REVIEW. É uma salvaguarda, não um bug a remover.
P2-08: scripts/check_dialogs.py usa mecanismo de desktop Win32 e diagnostica só janelas Abrir/Open; não demonstra ausência de outros modais nem garante perfil correto.
P2-09: hooks da interface do Facebook podem mudar. Manter seletores ancorados em modal e fail-closed como PR #6.

## Código implementado na Fase 8
- app/daily_queue.py: nova tabela jobs_v2 com UNIQUE(day,slot,group_id). A tabela jobs legada fica intacta; importação é INSERT OR IGNORE.
- Planejamento justo por menor número de usos no dia, com desempate embaralhado determinístico por rotation_seed/dia.
- groups_per_slot=3; max_posts_per_group_per_day mantém default 1. Somente opt-in explícito com max_posts_per_group_per_day=3 e allow_repeat_group_per_day=true permite até 12 no dia com 4 grupos. Essa frequência exige compatibilidade com regras de cada grupo.
- Plano de um dia torna-se imutável após a primeira geração; não acrescenta jobs ao modificar config ou reiniciar processo.
- scripts/daily_tick.py retorna BLOCKED_CONTENT e evento PREFLIGHT_FAILED para arquivo alterado/ausente, sem enviar, e sinaliza falha no exit code do Windows.
- GET /api/schedule e GET /api/schedule/events/{id}: leitura de SQLite local, sem navegar Facebook; HTML mostra slots, IDs, criativos, status e alertas de pendência.
- config/daily.example.json: 08:00, 12:00, 18:00, 20:00, 4 IDs FICTÍCIOS, fotos simples, sequência de 3 fotos e vídeo. enabled=false, allow_unattended=false.
- scripts/install_windows_scheduler.ps1: mostra máximo teorico de envios e verifica desvio do fuso local. NÃO instala sem -Install e habilitação explícita.
- Testes: quatro grupos, três por slot, 12 jobs, default uma vez/grupo/dia, esquema legado intacto, replanejamento idempotente e erros de integridade.

## Dois cenários possíveis para interpretar o pedido
A) Quatro grupos cadastrados, selecionar TRÊS POR HORÁRIO (4 horários) = até 12 posts/dia. Exige explicitamente repetir grupo até 3 vezes/dia e verificar permissão dos grupos.
B) Quatro grupos cadastrados, publicar em TRÊS GRUPOS NO DIA = 3 posts/dia. Configurar groups_per_slot=1, max_posts_per_group_per_day=1 e selecionar até 3 horários ou uma estratégia de limite diário; não usar o exemplo A automaticamente.

## Sequência de homologação Windows (sem testes reais repetitivos)
1. Preservar data/, sessões e banco original. Fazer cópia segura do SQLite via API sqlite3.backup, incluindo WAL, e nunca apagar arquivos históricos.
2. Atualizar branch e ler AGENTS.md/skill fase8; garantir CI e /health.build_revision iguais ao HEAD final.
3. No Chrome, observar que contas, grupos e login estão corretos. Confirmar que os quatro grupos permitem publicidade e frequência pretendida. Verificar post anterior no feed.
4. Criar data/daily.json com URLs reais, caminhos locais de JPG/PNG/MP4 e textos autorizados, inicialmente enabled=false.
5. Em banco de homologação separado, gerar plano para data futura (não sobrescrever plano existente de hoje). Verificar 4 slots×3 = 12 jobs, 3 por grupo/dia, horários +10/+20 por janela, nenhuma repetição de grupo dentro do slot.
6. Validar hashes dos bytes, grupos/legendas escolhidos, editor seguro, vídeo e galeria, mudanças de arquivo depois do planejamento, horários perdidos, duas instâncias concorrentes e reinício.
7. Validar endpoint /api/schedule e UI. A fila deve mostrar PLANNED, NEEDS_REVIEW, VERIFIED_EXTERNALLY, MISSED.
8. Testar Task Scheduler em preview, validar fuso e triggers corretos. Não instalar ainda.
9. Teste único autorizado no Grupo B (ou grupo designado), confirmar por URL/permalink e mídia, registrar a prova; se não houve prova, manter NEEDS_REVIEW.
10. Somente após autorização do operador e confirmação do fluxo, habilitar enabled=true / allow_unattended=true e instalar com -Install. Não fazê-lo só porque os testes offline passaram.
11. Conferir a tarefa Windows depois do registro: usuário interativo, sessão logada, Python .venv, limite 30min, MultipleInstances=IgnoreNew e StartWhenAvailable=false.
12. Se um post gerar SUBMITTED_UNVERIFIED, suspender os próximos conforme política existente. Evitar qualquer auto-retry após clique.

## Observabilidade necessária para produção contínua
O agente pode inspecionar por ID a dupla (job_id, operation_id) e correlacionar o ledger SQLite, operations.jsonl e o feed. Ainda faltam prova automática de publicação/URL, associação de identidade Facebook real, e fluxo de conciliação externa sem intervenção repetitiva. Nenhum destes foi falsamente marcado como pronto nesta PR.

## Referências de engenharia
- Playwright Python locators: https://playwright.dev/python/docs/locators
- Task triggers: https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasktrigger
- Task settings IgnoreNew: https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset
- Meta API Groups (publish_to_groups removida em 2024): utilizar Chrome somente em grupos permitidos, sem APIs privadas ou evasão.
