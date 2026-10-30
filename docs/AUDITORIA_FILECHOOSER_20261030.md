# Auditoria P0 de FileChooser, colagem de imagens, vídeos e revisão do processo — 30/10/2026

## Escopo e prova
Base: PR #1 / `9c978197`, relatório de homologação no Windows e screenshots fornecidos pelo operador.
- Fotos 2 e 6: os testes locais do Antigravity e as capturas sustentam que posts apareceram no feed. Não transferir essa prova para a nova implementação sem novo teste.
- Vídeo 28,4 MB: há prova de envio e início de processamento, mas **não prova de reprodução integral**, conclusão de transcodificação ou permalink direto.
- A janela nativa **Abrir** aberta após o post é um defeito operacional. A função antiga chamava `mb.click()` e depois `fi.set_input_files(media)`; ela misturava mecanismos distintos e podia deixar diálogo Windows aberto.
- `submit-intents/<uuid>` impede que este fluxo classifique um clique ambíguo como seguro para retry, mas NÃO garante exatamente-uma-vez entre requisições diferentes, processos concorrentes, intervenção manual, falha de disco ou reinício da máquina.

## Correção cirúrgica nesta branch
1. `app/browser.py`: se existir input correto no diálogo de composição, `set_input_files` diretamente, **sem clicar Foto/vídeo**.
2. Quando o input surgir apenas depois da ação, usar `page.expect_file_chooser()` e `chooser.set_files()`, método oficial Playwright; não abrir seletor Windows em paralelo.
3. `app/media_checks.py`: seleção por tipo de input, exigência de prova quantitativa `preview_visivel + selo +N = total esperado`, com `input.files == total` ao usar colagem. Botão genérico Editar não basta. Falhar fechado em ambiguidade.
4. `app/browser.py`: reconferir legenda após anexar mídia e imediatamente antes do clique para prevenir publicação sem texto por re-renderização do compositor.
5. `app/media_policy.py`: orçamento de espera por tamanho, mínimo 240s, teto 600s. **Não é garantia** para 300 MB, pois conexão e processamento dependem do Facebook.
6. `app/telemetry.py`: `UPLOAD_ROUTE_SELECTED`, `observed_count`, `overflow_count`, `CAPTION_RECHECK_PASSED` sem texto, path ou imagens.
7. `app/main.py`: `/health` expõe `build_revision`, `pid`, `busy` e mantém `real_facebook_publish_verified=False`; trocar grupo, conta ou navegador fica bloqueado durante publicação.
8. `start-windows.ps1`: detecta servidor ainda aberto com commit diferente e encerra com `STALE_SERVER`, em vez de abrir UI antiga. Não mata PID sem checar upload ativo.

## Validações / critérios de aceite
- CI Python e testes de seletores/colagem/legenda, incluindo execução real do JS da galeria em fixture DOM simulada se Node presente.
- No Windows, após concluir os posts **já realizados**, fechar MANUALMENTE a janela nativa remanescente uma única vez pelo botão Cancelar. Não usar Alt+F4 cegamente.
- Atualizar branch sem apagar `data/`; validar `/health.build_revision` igual a `git rev-parse --short=12 HEAD`.
- Selecionar vídeo de teste 1× e confirmar que `UPLOAD_ROUTE_SELECTED= DIRECT_INPUT` (ou fallback `PLAYWRIGHT_FILE_CHOOSER`) e **nenhum seletor nativo Windows permanece aberto**. Apenas 1 envio real com autorização.
- Selecionar 6 imagens de teste, constatar badge `+2` e prévias visíveis; se `MEDIA_PREVIEW_INCOMPLETE`, salvar apenas metadados e inspecionar DOM visualmente. Não desabilitar validação.
- Testar re-renderização de legenda em fixture e resultado `CAPTION_LOST_AFTER_UPLOAD` antes de `SUBMIT_INTENT`.
- Após teste real de vídeo, aguardar o Facebook concluir processamento e reproduzir um trecho. Se ainda carregando, manter `SUBMITTED_UNVERIFIED` / processamento pendente.
- Troca de grupo e conta durante operação deve retornar 409, sem interromper upload ou alterar destino.
- Não rodar repetidamente a mesma postagem de homologação para "comprovar robustez" sem verificar o feed e obter aprovação.

## Riscos ainda não resolvidos
- A colagem do Facebook varia por interface/idioma: o selo pode não ser texto folha ou os previews podem mudar de URL. O sistema interrompe em dúvida e o Antigravity corrige seletor com evidência real.
- O marcador durável não substitui uma fila persistente com chave de idempotência por campanha/destino/conteúdo. Não anunciar exatamente-once como garantido.
- O vídeo pode continuar processando depois que os arquivos temporários forem limpos; confirmar no Facebook antes de afirmar resultado final.
- Verificação de permalink, autenticação da identidade "postando como", dedupe entre requisições e agendamento recorrente são próximos estágios separados.
- Não habilitar captura HTML, screenshots ou tracing de sessão por padrão: podem conter dados privados.
- Não mesclar até os gates locais e revisão visual passarem.

## Documentação oficial
- https://playwright.dev/python/docs/input — locator.set_input_files e FileChooser
- https://playwright.dev/python/docs/api/class-filechooser — file_chooser.set_files, is_multiple
- https://playwright.dev/python/docs/actionability — validação de visibilidade e botão habilitado
