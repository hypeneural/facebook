# Antigravity 2.0 — arquitetura AI-first em 29/10/2026

Docs oficiais:
- https://antigravity.google/docs/models — Gemini 3.8 Flash, thinking Low/Medium/High.
- https://antigravity.google/docs/skills — formato SKILL.md.
- https://antigravity.google/docs/migration/workflows-to-skills — workflows antigos encerrados em 19/10/2026.
- https://antigravity.google/docs/rules — AGENTS.md descoberto automaticamente.
- https://playwright.dev/python/docs/api/class-browsertype — perfil persistente SEPARADO do Chrome pessoal.

Preferir Gemini 3.8 Flash / Medium. Usar High somente para diagnóstico que exige mais raciocínio. A operação atual é MVP: um grupo autorizado e uma publicação por execução.

Fluxo: abrir projeto -> /mvp-local -> script Windows prepara dependências -> testes offline -> servidor -> painel -> Chrome separado -> login pessoal se necessário -> grupo/foto -> autorização explícita -> publicar uma vez -> confirmar no Facebook.

O operador não deve clonar, configurar Python ou depurar manualmente. O agente toma essas ações, sem pedir segredos. Só pedir interação indispensável de login/2FA e autorização para publicar.

Não inferir POSTADO de sucesso HTTP, clique ou testes. Não repetir SUBMITTED_UNVERIFIED. CI não testa o site real do Facebook.
