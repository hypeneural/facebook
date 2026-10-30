# Revisão forense da Fase 5 — Editor Lexical e integridade das evidências

## Escopo confirmado
- PR #5 HEAD `0ff7584`: `fix(composer)` adicionou polling ao editor Lexical e dois seletores globais `[contenteditable="true"]`.
- CI da PR #5 aprovado; relatório do Antigravity declara troca do Grupo A (`464027871072447`) para o Grupo B (`389335997243726`).
- Postagem de foto no Grupo B: operação `bfaa51df-d5f8-44bf-8b7d-cd7c7a9edfaf` terminou `POST_UI_CLOSED_UNVERIFIED`, não prova publicação visível.
- Relatório G02 cita revisão do servidor `dfb8a655d2e9`, anterior ao commit final `0ff7584`; é preciso repetir o health com a revisão final antes de qualquer homologação nova.
- G06 usou ID inexistente e observou compositor indisponível. O teste de redirecionamento explícito para outro ID existe offline, mas não foi reproduzido ao vivo.

## Causa do hotfix desta PR
`app/browser.py EDITORS` na versão homologada pelo Antigravity passou a permitir seletores globais. Isso pode encontrar um `contenteditable` pertencente a comentário ou mensagem, preenchendo o lugar errado.
O código também usava `_find(EDITORS)` na reconferência da legenda, ampliando o risco após upload/React re-render.

## Correção mínima
- Substituir `EDITORS` por `EDITOR_SCOPE='[role="dialog"] [contenteditable="true"]'`: jamais pesquisar editores globais.
- `_find_editor(timeout_ms=6000)` espera a montagem do Lexical, verifica visibilidade/editabilidade, exclui artigos e indicações textuais de comentário, e falha caso encontre múltiplos editores elegíveis.
- `_assert_caption` usa a MESMA busca restrita. Nenhum clique de postagem é feito se a legenda foi perdida ou o editor é ambíguo.
- `app/telemetry.py` classifica `EDITOR_AMBIGUOUS` e `CAPTION_EDITOR_NOT_FOUND` sem registrar o texto da legenda.
- `tests/test_editor_scope.py` cobre seletor restrito, comentário recusado, ausência de diálogo, dois editores ambíguos, reconferência da legenda e códigos de erro.

## Pré-merge no Antigravity
1. **Sem reiniciar navegação ativa:** conferir se `bfaa51df` apareceu realmente no feed do Grupo B e se vídeo `24d12f3b` é reproduzível. Se resultado incerto, não repetir postagem.
2. Fazer checkout da branch nova preservando `data/`, perfis e grupos. Não usar reset, force ou limpeza de cookies.
3. `/verificar-mvp`, `pytest`, CI verde, `/health.build_revision` = HEAD de fato.
4. Grupo B autorizado: abrir compositor sem clicar Publicar. Confirmar no DOM que o editor está dentro de `[role=dialog]` e não em comentário do feed. Testar abertura lenta 0,8–1,5 s.
5. Executar testes offline de comentário concorrente e múltiplos editores. Se há ambiguidade real, corrigir o seletor com prova local; não restaurar fallback global.
6. Somente depois, com autorização explícita, UM post de teste; exigir evidência no feed e mídia correta.
7. Reportar PASS/FAIL/NÃO TESTADO. Não fazer merge até correção testada no Windows.

## Limites conhecidos
- O único fluxo de conta/grupo é sequencial, sem agendamento.
- `group_url` comprovado + editor presente não comprovam permissão real para publicar.
- `POST_UI_CLOSED_UNVERIFIED` não é `VERIFIED_EXTERNALLY`; faltam permalink/conferência da mídia.
- Proteções locais de `submit-intents/<id>` não equivalem a exatamente-uma-vez entre campanhas diferentes.

Fontes oficiais: https://playwright.dev/python/docs/locators e https://playwright.dev/python/docs/actionability

## Complemento: segunda validação de destino imediatamente antes do clique
O hotfix agora chama `_assert_target_group` tanto depois da navegação quanto após upload/legenda e **antes do marcador durável SUBMIT_INTENT**. Se a aba mudar do Grupo B para A durante a preparação, a operação é bloqueada pré-clique com `GROUP_DESTINATION_MISMATCH`. Inclui teste simulado para a troca tardia de URL. Não prova a identidade da pessoa nem a permissão no grupo; são gates posteriores.
