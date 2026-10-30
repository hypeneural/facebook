# Plano anti-alucinação — adoção de ideias após PR #1

**Não executar agora:** o Antigravity está homologando a PR #1. Esta documentação não altera runtime.

## Ordem dos hotfixes
1. **P0 CAPTION_RECHECK** — após anexar mídia, `app/browser.py` reconfere texto esperado do editor; aborta antes de clicar se texto perdido. Fixture de re-renderização; PASS se nenhum `SUBMIT_INTENT` ao perder legenda.
2. **P0 COMPOSER_SCOPE** — testar UI PT-BR que contém feed + comentários. Confirmar um único compositor correto e botão correto. Não usar `.first`/ `.last` globais para decisão crítica.
3. **P0 PROCESS_REVISION** — no `/health`, expor versão do build, e no bootstrap verificar que corresponde ao checkout para evitar testar código antigo ainda em memória.
4. **P1 SESSION/IDENTITY** — distinguir `LOGIN_REQUIRED`, `CHECKPOINT`, `GROUP_PERMISSION`, `POST_AS_PAGE`; mostrar conta ativa na prévia. Nunca trocar/contornar identidades.
5. **P1 EVIDENCE** — `VERIFIED_EXTERNALLY` só com evidência inequívoca; não inferir do diálogo fechado.
6. **P2 CAMPAIGN QUEUE** — somente depois de 2–10 fotos, vídeo e 2 perfis homologados; SQLite em vez de JSONL como fonte de verdade de scheduler.

## Contratos operacionais
- Exclusivo: no máximo um navegador/perfil publicando por vez.
- Nunca publicar sem autorização e sem mídias prontas.
- Ao encontrar resultado ambíguo, suspender o destino específico até inspeção.
- Logs não contêm texto da legenda, fotos, URLs com tokens, cookies ou HTML da sessão.
- Código atualizado no GitHub ≠ aplicação local recarregada.
- Estado de fila deve diferenciar `PENDING_REVIEW`, `SUBMITTED_UNVERIFIED`, `VERIFIED_EXTERNALLY`, `PRE_SUBMIT_FAILED`.

Ver fundamentação e arquivos exatos em [FORENSE_BENCHMARK_AUTOMACAO_GRUPOS_20261029.md](FORENSE_BENCHMARK_AUTOMACAO_GRUPOS_20261029.md).
