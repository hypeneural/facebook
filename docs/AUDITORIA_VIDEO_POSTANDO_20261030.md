# Auditoria P0: Facebook permanece "Postando" depois do clique (30/10/2026)

## Fonte e escopo
Base: `hypeneural/facebook` PR #3 commit `67da3a6`, documentação oficial Playwright,
relatório de homologação local Antigravity e screenshot enviado pelo operador.
O vídeo MP4 de ~28,49 MB gerou operação `a5a3a331-12e8-41c7-a82e-36c34cc2cb6a`
e estado `SUBMITTED_UNVERIFIED` após cerca de 7,3 segundos. A imagem mais recente
mostra claramente uma **sobreposição "Postando" dentro do compositor**. Não é
evidência de publicação concluída, erro definitivo ou vídeo reproduzível.

## Causa direta demonstrada
`app/browser.py._publish` fazia `btn.click(...)`, esperava 1,9 segundo e retornava
`SUBMITTED_UNVERIFIED`. Seu encerramento liberava o `publish_lock` mesmo se
a interface continuasse "Postando". Um novo `page.goto`, troca de grupo ou
perfil podia interromper o mesmo compositor, sem rastreabilidade posterior.

## Hotfix conservador
- `app/post_state.py`: classificação SOMENTE por sinais visíveis e sem retornar
  legendas, DOM, cookies, URLs ou mídia. Sinais: `POSTING_IN_PROGRESS`,
  `VIDEO_PROCESSING`, `PENDING_REVIEW`, `FACEBOOK_WARNING`,
  `POST_UI_CLOSED_UNVERIFIED`, `DIALOG_OPEN_UNVERIFIED`.
- Após o clique, o Browser monitora transições de UI por até 90 s (vídeo) ou
  45 s (imagem). São limites do monitor, **não limites de upload Facebook**.
  Registra `POST_UI_OBSERVED` e `POST_MONITOR_LIMIT`; se "Postando" continua,
  retorna `post_ui_state=POSTING_STILL_VISIBLE` com
  `status=SUBMITTED_UNVERIFIED`. NÃO espera indefinidamente.
- `GET /api/post-state`: consulta SOMENTE leitura da aba atual, sem navegar,
  atualizar ou tentar publicar. O painel apresenta o estado e a operação.
- Antes de nova publicação/troca de grupo/conta, detecta post anterior ainda
  aberto e falha com `PREVIOUS_POST_STILL_ACTIVE`. NÃO fecha modal nem reenvia.
- Fotos/vídeo continuam usando o `SUBMIT_INTENT` durável da PR #1. A marca evita
  retry acidental dentro do fluxo, mas não produz garantia global exactly-once.
- A UI de acompanhamento não declara publicado quando o diálogo desaparece.
- O script só monitora o DOM local, NÃO captura tráfego de autenticação nem
  usa APIs privadas do Facebook.

## Limitações (não declarar PASS baseado só em CI)
1. Indicador "Postando" não diz se upload está lento, transcodificação prossegue,
   rede caiu ou Facebook ficou bloqueado. O diagnóstico preciso exige observação
   manual do Facebook e, se necessário, inspeção local não sensível do navegador.
2. Processamento de vídeo pode durar além dos 90 s de monitoramento. A UI
   continua aberta; `GET /api/post-state` permite conferir mais tarde, sem
   reenvio e sem encerrar o Chrome.
3. O aviso "Processando vídeo" pode aparecer fora de `role=status/alert`
   dependendo da variante A/B. Não adotar silêncio do banner como prova de sucesso.
4. `POST_UI_CLOSED_UNVERIFIED` quer dizer apenas que o compositor sumiu.
5. Não existe verificação automática de permalink nem de reprodução completa.

## Homologação local Antigravity (sem duplicar posts)
1. Fazer checkout da PR Draft derivada da PR #3, preservando `data/`, sessões,
   `accounts.json`, `groups.json` e marcadores; sem reset/force.
2. Executar testes offline e conferir `/health.build_revision` igual ao HEAD.
3. **Antes de qualquer post novo**, inspecionar na aba existente se o envio
   `a5a3a331...` ainda mostra "Postando"; não dar refresh, não clicar novamente,
   não fechar o modal ou reiniciar Chrome enquanto resultado estiver incerto.
4. Verificar na interface, sem postar, `GET /api/post-state` e confirmar o
   estado `POSTING_IN_PROGRESS` (se visível) ou `POST_UI_CLOSED_UNVERIFIED`
   se encerrado; registrar operação e transições JSONL.
5. Só após esclarecer a operação anterior, homologar UM vídeo curto em grupo
   autorizado, com autorização explícita do gestor. Verificar cronômetro,
   eventos, retorno no painel e reprodução do vídeo no feed.
6. Nunca criar segundo envio por timeout, retorno 200, modal fechado ou CI verde.
7. Reportar PASS/FAIL/NÃO TESTADO por etapa e nenhum dado privado nos logs.

## Próximos refinamentos após homologação
- Instrumentar eventos de rede estritamente de **metadata agregada** (não headers,
  URLs, corpos ou tokens) somente se a UI permanecer inexplicavelmente bloqueada.
- Identificar identidade "Postando como" e grupo antes do clique.
- Confirmação manual/externa de permalink e reprodutibilidade do vídeo.
- Fila SQLite com idempotência por campanha/destino/ocorrência depois de MVP real.

## Fontes oficiais
- https://playwright.dev/python/docs/api/class-page (wait_for_function,
  browser events, wait_for_timeout desencorajado)
- https://playwright.dev/python/docs/api/class-locator (wait_for, actionability)
- https://playwright.dev/python/docs/events
