---
name: fase4-video-posting
description: Homologa diagnostico de carregamento "Postando" apos clique de video, sem fechar navegador e sem reenviar; monitora estados e previne navegacao enquanto post estiver ativo.
---

# /fase4-video-posting

Use Gemini 3.8 Flash Medium. Siga esta ordem sem improvisar.

1. Checkout da branch `fix/video-posting-state-watchdog-20261030`, preservando
   alterações e `data/`. Não fazer merge nem reset.
2. Ler `AGENTS.md` e `docs/AUDITORIA_VIDEO_POSTANDO_20261030.md`.
3. Rodar `/verificar-mvp` uma vez; conferir revisão em `/health`. Se servidor
   anterior estiver em operação (`busy=true`), NÃO encerrar processo.
4. **Antes de nova postagem**, verificar situação da operação MP4 anterior
   `a5a3a331-12e8-41c7-a82e-36c34cc2cb6a`. Se a mesma aba mostrar
   "Postando", não atualizar, fechar ou iniciar outro envio. Registrar o que
   foi observado sem conteúdo privado.
5. Verificar `GET /api/post-state` e botão "Conferir publicação em andamento".
   Endpoint é apenas leitura. Se reinício perdeu correlação, consultar o
   `operation_id` persistido em `data/operations.jsonl`; nunca inventar
   estado confirmado.
6. Validar offline os estados `POSTING_IN_PROGRESS`,
   `POSTING_STILL_VISIBLE`, `VIDEO_PROCESSING`, `PENDING_REVIEW`,
   `POST_UI_CLOSED_UNVERIFIED`, `FACEBOOK_WARNING`.
7. Validar que tentar trocar conta/grupo ou publicar enquanto "Postando"
   resulte em `PREVIOUS_POST_STILL_ACTIVE` antes de qualquer clique.
8. Após resolução verificada do envio anterior, apresentar conta, grupo,
   legenda e mídia de teste; pedir autorização explícita e fazer, no máximo,
   UM novo envio real. Monitorar sem reenvio e verificar se vídeo é
   reproduzível no feed ou permanece pendente.
9. Se layout A/B impedir classificar a UI, corrigir exclusivamente o seletor
   demonstrado, com teste offline correspondente; não introduzir automação
   de bypass, proxies, screenshots privadas ou APIs privadas.
10. Finalizar com PASS/FAIL/NÃO TESTADO, operação, status e evidência real.
    Não declarar postagem pública apenas por clique, desaparecimento do
    spinner ou CI verde. Deixar PR Draft até validação real.
