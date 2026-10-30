# Auditoria forense comparativa: automação resiliente de grupos Facebook (29–30/10/2026)

**Status:** pesquisa técnica de leitura. **Não altera código de execução.** Documento isolado da PR #1 para não atrapalhar a homologação local do Antigravity.

## 0. Fonte e método

Fonte de verdade do nosso MVP: [`hypeneural/facebook`](https://github.com/hypeneural/facebook), `main` 2f2b789 (foto única com evidências) e [PR #1](https://github.com/hypeneural/facebook/pull/1) (Draft: mídia múltipla, vídeo, perfis/grupos, auditoria, ainda sem homologação de novos cenários). Foram examinados arquivos de implementação, testes, histórico de commits, licença e mecanismos de resultado dos projetos abaixo. **Testes declarados pelos repositórios não equivalem a publicar ao vivo.**

Referência oficial para esperas e seletores: https://playwright.dev/python/docs/actionability e https://playwright.dev/python/docs/api/class-locator . A API oficial `publish_to_groups` foi descontinuada em 22/04/2024; automação de UI pode quebrar com alterações do Facebook. Respeitar as regras de cada grupo, não tentar driblar CAPTCHA, bloqueios ou políticas.

## 1. Benchmarks de código (não copiar arquivos de projetos sem licença!)

### A. `WahuVN/facebook-group-poster` — melhor inspiração **para resiliência e diagnóstico**
- Fonte: https://github.com/WahuVN/facebook-group-poster
- `fb_group_poster.py:74–82,173–255`: `AmbiguousPublishStateError` separado, classificação `transient_network`/ `non_retryable`/ `publish_state_ambiguous`, retry exponencial limitado **somente para operação idempotente escolhida**; testes `tests/test_core.py:70–122`.
- `fb_group_poster.py:83–157`: `JsonlEventLogger` com `run_id` e sanitização recursiva de campos sensíveis, arquivos em `LOCALAPPDATA`; testes de redaction em `tests/test_core.py:124–147`.
- `fb_group_poster.py:638–663`: `wait_post_done` aceita fechamento do diálogo ou mensagens de confirmação, mas não é prova de permalink. Uma saída ambígua **não é reenviada**.
- `fb_group_poster_gui.py`: fila visual, importar/exportar listas de grupos, seleção, agendar por intervalo, botão de parada e indicadores de progresso. Útil na UX, mas não precisamos de Tkinter: nosso painel FastAPI já existe.
- **Problemas:** `upload_video` tenta input global após o diálogo — exatamente a classe de bug já corrigida no nosso MVP; guardar estado exportado tem risco de segredo; ausência de licença explícita na API GitHub. **Copiar apenas a estratégia, nunca o código.**
- **Adotar:** códigos de erro por etapa, parada segura e teste de navegação idempotente; relatórios por `run_id`. Já existe `operation_id` na PR #1, não criar segundo ID para a mesma tentativa.

### B. `thenotoriousmrkrabs/opencli-plugin-fb-autopost` — melhor inspiração **para pré-submit**
- Fonte: https://github.com/thenotoriousmrkrabs/opencli-plugin-fb-autopost
- `group-post.js:25–85`: verifica grupo, abre compositor, insere legenda, anexa imagens, **confere novamente a legenda após anexar mídia**, revalida estado de segurança antes de clicar, oferece `dry-run-ready` sem clique, e `confirm` explícito para live.
- `src/composer.js:173–221,384–430`: verifica que o texto realmente está no editor e avalia resultado em estados `waiting`, `pending-review`, `failed`, `posted`. Atenção: "dialog closed" é evidência fraca de postagem pública, não a classificar como verificada.
- `src/images.js:53–80,133–179`: conta prévias e botões de remoção, teste de compatibilidade; envolve Browser Bridge e fallback DataTransfer/base64 inadequados para nosso MVP.
- `src/auth-detection.js:1–113`: classificador para login, checkpoint, CAPTCHA, ação bloqueada e aviso de intervenção manual; **nunca tentar contornar**.
- Testes `tests/group-post.test.js` abrangem legenda perdida após upload, preview antes de publicar, dry-run e revisão.
- **Problemas:** dependência OpenCLI/Browser Bridge, screenshots potencialmente privadas, o critério "diálogo fechado" ainda pode ser falso positivo; licença exige verificação específica. **Adotar:** revalidar legenda e destino IMEDIATAMENTE antes do clique, detectar estados de bloqueio, dry-run/preflight sem publicação.

### C. `phantakanxm/facebook-group-autopost` — melhor inspiração **para modelo de dados/agenda (futuro)**
- Fonte: https://github.com/phantakanxm/facebook-group-autopost
- `packages/db/prisma/schema.prisma`: separa User, Group, Campaign, CampaignGroup, PostLog, Setting; `@@unique([userId, fbGroupId])` e `@@id([campaignId, groupId])`, modelos de agenda e tentativas por grupo. **Boa inspiração de SQLite**, sem importar Prisma/Electron.
- `apps/worker/src/campaigns/runner.ts:44–81`: claim atômico `scheduled -> running`; verifica sessão antes da campanha; grupos concluídos filtrados para retomada.
- `apps/worker/src/campaigns/runner.ts:94–187`: cancela quando status muda; pausa a campanha por sessão inválida, conta bloqueada, limitação, ou falhas consecutivas.
- `apps/worker/src/playwright/detect.ts`: estados explícitos `session_invalid`, `account_locked`, `rate_limited`, `group_unavailable`.
- `apps/worker/src/groups/sync.ts`: detecta lista de grupos virtualizada e usa rolagem até estabilizar o número de links; deduplica por `fbGroupId`. **Somente se no futuro for necessário descobrir grupos que o operador autorizar**; agora priorizar grupos salvos.
- `apps/worker/src/logger.ts`: logger `pino` com contexto da campanha, logs locais.
- **Falhas a NÃO copiar:** `apps/worker/src/playwright/post.ts:95–111` marca `success: true` ~4 s após clique, inclusive aprovação pendente; `runner.ts` usa sucesso incerto para pular o grupo em retomada e faz retry automático para resultados `failed`; `browser.ts` exclui arquivos SingletonLock/Cookie do perfil e aplica stealth/user-agent estático. Isso pode gerar corrupção de sessão, postagem duplicada ou risco de restrição. O repo **não possui licença declarada**.
- **Adotar depois da homologação:** tabelas Campaign/Target/Attempt, agrupamento por conta/grupo, scheduler local simples, pausa de execução e cancelamento antes do clique.

### D. `hthmkt12/flowkit` (FBKit) — melhor inspiração **para invariantes e concorrência**
- Fonte: https://github.com/hthmkt12/flowkit (MIT)
- `agent/services/safety_gate.py:74–123`: fingerprint de conteúdo normalizado + destino e avaliação local de limites. Útil como **alerta de possível duplicidade**; não bloqueia postagens legítimas automaticamente sem revisão do operador.
- `agent/db/crud.py:262–285,577–625,756–792`: claim com transição condicional, lease por conta, expiração e liberação de trabalho; interessante quando houver fila no futuro.
- `agent/worker/processor.py:85–109`: classifica erros e backoff; `possible success` é não-retryable. A própria lista de retries gerais é permissiva demais para nosso caso sem prova de pré-clique.
- `agent/services/fb_client.py`: roteamento por `fb_uid` e heartbeat da sessão para evitar associar tarefas à conta errada. No MVP usar sessão/identidade confirmada sem extensão/websocket.
- Testes `tests/unit/test_duplicate_fingerprint.py`, `test_retry.py`, `test_multi_profile_sessions.py`.
- **Problemas a não copiar:** complexidade de extensão/WS, ações live desativadas por padrão, integração Cloud e políticas de aprovação excessivas para o MVP; evitar suas exceções de autenticação loopback e o uso de chaves padrão.
- **Adotar:** identidade vinculada à conta esperada, fingerprint local, proteção contra concorrência e diferenciação entre resultado incerto e seguro para reenvio.

### E. `AhmedNasser1010/fb-group-poster` — melhor inspiração **para evitar comentários acidentais e identidade Page**
- Fonte: https://github.com/AhmedNasser1010/fb-group-poster
- `src/lib/facebook/poster.ts:9–55,80–143`: exclui caixas `Comment as…`/comentários do seletor de compositor e avalia dicas de permissão, moderação, grupo inacessível.
- `poster.ts:195–216`: distingue postar como Page vs perfil e alerta quando o grupo não permite publicação por Page. Fundamental caso o Facebook mude identidade ativa no topo do compositor.
- `poster.ts:240–265`: verifica texto do editor e respeita que Enter em comentários pode enviar inesperadamente.
- `poster.ts:338–372`: aguarda a janela depois do clique, lê avisos, mas ainda pode declarar `success` por fechar diálogo ou por timeout incerto. **Não copiar esse estado de sucesso.**
- **Bug crítico no fonte:** `poster.ts:269–310` captura falha de upload com `catch {}` e continua publicando **sem foto**. Proibido em nosso projeto.
- Sem licença declarada: inspiração arquitetural somente.
- **Adotar:** guarda explícita `NOT_COMMENT_BOX`, `POST_AS_IDENTITY_MISMATCH`, `GROUP_PERMISSION_UNAVAILABLE` e bloqueio preventivo antes do clique.

### F. `0xEnc0der/fbcli` — o que aproveitar e o que NÃO aproveitar
- Fonte: https://github.com/0xEnc0der/fbcli (MIT)
- `fbcli/web_actions.py:320–379` observa respostas GraphQL para extrair permalink; se não encontrar, **devolve URL genérica do grupo e a trata como permalink**. Isso é falsa evidência. Não utilizar GraphQL privado nem exportação de cookies.
- `fbcli/browser.py` injeta cookies exportados em Chromium; nosso perfil persistente é melhor para proteger segredo e simplificar.
- **Adotar:** distinção entre `verified_post_permalink` e URL genérica de grupo; somente marcar publicação `VERIFIED_EXTERNALLY` quando link direto `/groups/ID/posts/POST_ID` foi realmente observado e validado na interface, com mídia verificada.

### G. `bryan-kier/fb-group-auto-poster`, `ariknih/autopost-facebook-group`
- `bryan-kier/poster.py:149–221`: histórico de grupos com exclusão de já postados; porém ao completar ciclo zera o log e pode repetir postagens, sem evidência forte após envio. Sem licença declarada. **Não copiar reset de ciclo**.
- `ariknih/main.py:41–48,89–173`: `LOOP_POSTING=True` e ciclos contínuos com contas e cookies JSON, classe chamada `FacebookGroupSpam`. Mesmo com MIT, é inadequado para nosso fluxo responsável e pode publicar conteúdo repetitivo. **Não importar.**

## 2. Gaps concretos no nosso MVP / PR #1

| Prioridade | Código atual | Fragilidade | Critério de melhoria |
|---|---|---|---|
| P0 | `app/browser.py` | Após upload não reconfirma se legenda ainda corresponde ao texto esperado | `CAPTION_RECHECK_PASSED`; caso contrário erro antes de `SUBMIT_INTENT` |
| P0 | `app/browser.py` | COMPOSERS/POST_BUTTONS podem confundir botão de compartilhar/comentar ou diálogos internos | Exigir o **compositor principal** identificado, jamais textbox de comentário; role + contexto + único alvo acionável |
| P0 | `app/browser.py` `_status` | Existência de cookie `c_user` é apenas indício de login, não confirma identidade correta/permissão no grupo | Mostrar identidade visível "Postando como" por perfil e grupo; não coletar segredo no log |
| P0 | `app/main.py` `/api/publish` | Antigravity pode puxar código novo e encontrar servidor velho reaproveitado pelo PowerShell | Expor `build_revision` em `/health` e reconciliar versão do processo antes de homologar |
| P0 | `app/browser.py` / telemetria | Não existe confirmação por permalink/mídia reproduzível; `SUBMITTED_UNVERIFIED` é correto | `VERIFIED_EXTERNALLY` apenas após evidência visível; `PENDING_REVIEW` separado |
| P1 | `app/main.py` | `publish_lock` protege upload/envio, mas ações de conta/grupo usam verificações não atômicas | Uma trava de ciclo de operação para troca de perfil, navegação e publicação; nunca mudar conta durante envio |
| P1 | `app/browser.py` | Seletores e prévias dependem de DOM com novas imagens externas; validação de 10 fotos não passou ao vivo | HTML fixtures PT-BR e 2/6/10 imagens; diagnosticar `EXPECTED_PREVIEWS` vs `OBSERVED_PREVIEWS` |
| P1 | `app/telemetry.py` na PR | Logs por operação bons, mas não há relatório agregado diário por causa, sucesso confirmado ou duração P95 | Painel com KPIs derivados de estados reais, sem inventar "publicado" |
| P1 | `app/main.py` | Arquivos são copiados por HTTP para `data/uploads` temporário; agendar conteúdo depois requer persistência | Quando chegar a agenda, `media_assets` com arquivo local persistente, tamanho, hash, disponibilidade e limpeza explícita |
| P1 | `app/browser.py` | Esperas fixas e timeout grande não equivalem a progresso real do vídeo | Estado `UPLOAD_IN_PROGRESS`, `PREVIEW_READY`, `PUBLISH_BUTTON_ENABLED`, `PROCESSING_UNVERIFIED` separados |
| P2 | `app/static/index.html` | Falta pausa/cancelar antes do clique, estado por grupo e conta, sem confirmação de conteúdo legível | Painel de prévia e timeline, botões só para ações seguras com status explícito |
| P2 | `app/main.py` / sistema | Sem scheduler local, sem detecção de computador suspenso; não há execução recorrente | SQLite e trabalho agendado por conta/grupo, executor único, pausar automaticamente ante resultado incerto |

## 3. Estado de publicação — contrato proposto

- `DRAFT` -> `PREFLIGHT` -> `MEDIA_READY` -> `SUBMIT_INTENT` (persistir em disco) -> `SUBMITTED_UNVERIFIED`.
- Só mudar para `VERIFIED_EXTERNALLY` após post encontrado no grupo **e mídia esperada presente**.
- Se Facebook disser que requer administração: `PENDING_REVIEW`; **não** considerar `VERIFIED_EXTERNALLY`.
- Se falhar **antes de SUBMIT_INTENT**: `PRE_SUBMIT_FAILED` e erro tipado; uma nova ação exige nova aprovação quando aplicável.
- Se processo cair depois de `SUBMIT_INTENT`: `SUBMITTED_UNVERIFIED`, nunca auto-retry.
- Se sessão perdeu validade, há CAPTCHA ou bloqueio: `PAUSED_MANUAL_ACTION` sem contorno.
- Nunca usar "formulário fechou" ou URL genérica do grupo como prova de post.

**Regra de ouro:** autonomia nos preparativos e diagnósticos, conservadorismo extremo na decisão de repetir uma publicação.

## 4. Próximos testes determinísticos (sem Facebook real)

1. Fixture PT-BR com compositor verdadeiro + comentários do feed, avatar e múltiplos diálogos; provar que escolhe o alvo correto ou falha fechado.
2. Após upload de 2 imagens, editor muda seu texto; confirmar que interrompe antes do clique com `CAPTION_LOST_AFTER_UPLOAD`.
3. Após escolher perfil local A, página ativa mostra identidade B; impedir clique e mostrar `POSTING_IDENTITY_MISMATCH`.
4. Primeiro upload falha ou perde miniatura; `MEDIA_PREVIEW_UNVERIFIED`, nenhum `SUBMIT_INTENT`.
5. Vídeo mantém processo por >90s sem sinal de pronto; reportar estado atual e tempo restante sem inventar sucesso.
6. Clique executado, servidor cai antes da resposta; reinicia, conserva marcador e nunca dispara novamente.
7. Git pull atualiza build mas servidor local ainda roda versão anterior; preflight detecta `BUILD_MISMATCH`.
8. Grupos iguais com URL variante/query; deduplica por ID canônico.
9. Resultado `PENDING_REVIEW` não entra no conjunto de `VERIFIED_EXTERNALLY`.
10. Sessão invalidada ou checkpoint exibido: pausa apenas o perfil afetado; nenhuma tentativa em grupo diferente.
11. Preflight com arquivos locais indisponíveis para campanha agendada: `MEDIA_SOURCE_MISSING` antes do clique.
12. Auditoria: nenhum log persistido inclui caption, cookie, perfil sensível, dump HTML ou arquivos privados.

## 5. Estratégia incremental segura

**P0 agora, enquanto a PR #1 é homologada (somente análise, sem código concorrente):**
- Rechecagem da legenda após upload.
- Pré-verificação da identidade "Postar como" e de que compositor ≠ comentário.
- Confirmação da versão de código em execução.
- Classificação do Facebook em login/checkpoint/permissão/limitação/pendente.
- Nunca alterar `main` nem publicar sem autorização.

**P1 depois que PR #1 estiver homologada e mesclada:**
- Indicadores de confiabilidade por `operation_id`, `account_id`, `group_id` e `media_kind`; métricas falha-pré-clique, incerto, pendente, verificado; tempos mediana/P95.
- Prova externa e revisão conservadora sem scraping intrusivo ou GraphQL privado.
- Botão de cancelar preparação (antes do clique), sem matar a sessão ou corromper a mídia.
- Seleção rápida de grupos e previsão de capacidade real por grupo (comentário vs discussão vs venda).

**P2 somente quando fotos/vídeo/contas estiverem homologados:**
- SQLite simples com `accounts`, `groups`, `campaigns`, `targets`, `attempts`, índice único `(campaign_id,group_id,scheduled_occurrence)`.
- Manifesto de mídia persistente com metadados e hashes, sem upload repetitivo de arquivos grandes.
- Agendador local único + serviço de inicialização Windows, com estado `RUNNING` reconciliado após reinício; não executar post se computador acordou atrasado sem política explícita.
- Repetição periodicizada por destino autorizado, com quotas de acordo com regras dos grupos, sem evasão de controles da plataforma.

## 6. Orientação ao Antigravity (não executar enquanto homologação atual estiver em andamento)

**Não alterar a PR #1 com estes itens por conta própria.** Usar esta auditoria como backlog para a próxima etapa. Quando a homologação atual terminar, propor alterações cirúrgicas, cada uma com reprodução em fixture, teste do contrato e um teste visual controlado. Não instalar Electron, extensão de terceiros, bibliotecas stealth, proxies ou cópias dos projetos estudados. Não copiar código de repositórios sem licença.

**Diligência:** muitas funcionalidades observadas são só arquitetônicas. Não há evidência nesta auditoria de sucesso real com vídeos em múltiplos grupos/contas para os repositórios pesquisados.
