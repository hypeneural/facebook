---
name: fase6-editor-seguro
description: Confere hotfix de editor Lexical restrito ao compositor no Windows, sem comentar nem postar no alvo errado.
---

# /fase6-editor-seguro

1. Checkout de `fix/lexical-editor-scope-safety-20261030` sem apagar perfis, sessões, histórico ou trabalho local.
2. Ler `docs/AUDITORIA_FASE5_REVIEW_EDITOR.md` e `AGENTS.md`.
3. Verificar antes de tudo o post `bfaa51df` no Grupo B e o vídeo `24d12f3b`, sem reenviar.
4. Rodar `/verificar-mvp` e confirmar a revisão carregada em `/health`.
5. Abrir somente o compositor em grupo autorizado. Esperar Lexical aparecer; verificar que o campo vem do diálogo de publicação, NÃO dos comentários.
6. Simular comentário visível + editor lento: o editor da legenda deve continuar correto; se não houver, abortar antes de clicar.
7. Confirmar `CAPTION_RECHECK_PASSED` somente quando a legenda estiver igual à esperada.
8. Um único envio real adicional APENAS se realmente necessário e com autorização explícita do operador.
9. Atualizar a PR com status real, logs sem conteúdo privado, PASS/FAIL/NÃO TESTADO. Não mesclar antes da homologação.
