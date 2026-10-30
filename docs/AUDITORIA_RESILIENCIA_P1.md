# Auditoria de resiliência e telemetria — P1

## Fonte
Branch PR #1 `audit/media-resilience-groups-profiles-20261029`; o MVP com foto única na main permanece intacto. Análise de código + comparação de princípios de FBKit/flowkit e facebook-group-autopost, não migração de código.

## Falhas concretas corrigidas nesta rodada
1. Resultados finais sem rastreabilidade entre API e navegador -> `operation_id` em evento, API, histórico e journal.
2. Ausência de progresso da operação -> eventos JSONL por estágio e painel `Diagnóstico da execução`, atualiza durante envio.
3. Falha do subprocesso do Playwright podia ser rotulada incorretamente como falha antes do clique -> verificar `SUBMIT_INTENT` durável antes de classificar o retorno.
4. Erros genéricos -> categorias de erro estáveis sem dados privados.
5. Nenhuma marcação de latência -> `duration_ms` nos principais marcos.
6. Falha inesperada após possível clique -> `SUBMITTED_UNVERIFIED`, sem retry.

## Eventos implementados
`REQUEST_ACCEPTED`, `FILES_STAGED`, `NAVIGATE_GROUP`, `COMPOSER_OPEN`, `CAPTION_FILLED`, `FILES_ASSIGNED`, `MEDIA_PREVIEW_READY`, `BUTTON_READY`, `SUBMIT_INTENT`, `SUBMIT_RETURNED`, `SUBMITTED_UNVERIFIED`, `PENDING_REVIEW`, `PRE_SUBMIT_FAILED`, `API_RESPONSE`.

Sem legenda, mídia, cookie, token, filepath, DOM ou screenshots no JSONL. Arquivo local: `data/operations.jsonl`, protegido por .gitignore. `GET /api/operations` exibe os últimos 30 trabalhos.

## Padrões úteis identificados em outros repos
- **FBKit `hthmkt12/flowkit`**: exceções que podem significar sucesso não são retryable; separar estado pré-despacho de pós-despacho. Não importar sua fila distribuída nem API cloud.
- **`phantakanxm/facebook-group-autopost`**: logger com contexto, categoria de falha por sessão/checkpoint e evidência por post. Evitar sua interpretação de pending-approval como sucesso definitivo.
- **Playwright oficial**: timeouts por elemento, locators semânticos, tracing opcional para diagnóstico. Traces contêm dados sensíveis; NÃO salvar nem exportar automaticamente.
- **`0xEnc0der/fbcli`**: ideia de confirmação por permalink, porém seu publicador não dá prova aplicável a vídeo/múltiplas fotos no FB atual; NÃO usar cookies exportados.

## Ações locais do Antigravity
1. `git status --short`; atualizar branch da PR #1 sem reset e sem perder `data/`.
2. `/verificar-mvp` uma vez; verificar `GET /api/operations` no painel.
3. Executar `/fase2-validar`; publicar foto de teste somente após autorização. Observar estágios no painel e confirmar `operation_id` idêntico no histórico e no JSONL.
4. Simular falha antes de clique em grupo de teste sem enviar, verificar `PRE_SUBMIT_FAILED`; NUNCA simular clique real para validar retry.
5. Duas fotos e MP4 só após testes individuais, sem publicações em lote. Inspecionar prévia e Facebook após clique. Log não deve conter material sensível.
6. Reportar tabelas de PASS/FAIL e, para cada falha, `operation_id`, `stage`, `error_code`, sem conteúdo de clientes.

## Fora do escopo desta PR
Scheduler periódico, postagem em massa, automação de contas em paralelo, proxies, sessão/cookies compartilhados, bypass Facebook, verificação automática robusta de permalink. 

## Segunda rodada: recuperação e desempenho
- `submit-intents/<operation_id>` é uma marcação local vazia, durável e pesquisada em O(1). Não depende de que a operação esteja entre os 100 registros recentes; evita classificação errada após muitos eventos.
- `GET /api/operations` retorna `next_action` para o Antigravity: por exemplo `VERIFICAR_NO_GRUPO_SEM_REENVIAR`.
- O painel lê no máximo o último 1 MiB do JSONL; não reprocessa todo o histórico em cada atualização.
- Rejeição de arquivo grande/vazio gera `UPLOAD_REJECTED` com ID da operação.
- O histórico é lido em streaming dos 20 registros mais recentes, tolerando uma última linha inválida.
- A troca de perfil recupera o identificador anterior se o Chrome falhar ao abrir o novo.
- A detecção de checkpoint é anterior à validação da URL de destino.

## Orçamento único de vídeo e fotos
O timeout de processamento agora é um único deadline para prévia e botão habilitado. Isso evita somar 4 minutos + 4 minutos; o clique recebe 20 s quando a mídia está pronta. O prazo é um limite técnico, não garantia do Facebook. Continuar conferindo o conteúdo depois da publicação.
