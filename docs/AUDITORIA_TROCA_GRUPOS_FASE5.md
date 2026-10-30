# Fase 5 — Auditoria da troca de grupos (30/10/2026)

Base: PR #4, commit 5669c54. O relatório da operação MP4 24d12f3b documenta POST_UI_CLOSED_UNVERIFIED, e **não** comprova vídeo publicado ou reproduzível.

## Problemas demonstrados na revisão do código
- _group() afirmava "Grupo aberto" só porque page.goto() retornou.
- Selecionar grupo salvo no painel não confirmava qual estava realmente aberto.
- O cadastro de grupos checava a trava sem adquiri-la (corrida).
- VIDEO_PROCESSING não bloqueava mudança de destino.
- A seleção de um perfil secundário não era persistida após reinício.

## Alterações nesta branch
- app/group_guard.py confirma domínio HTTPS Facebook e igualdade exata do ID do grupo após redirecionamento. Distingue login/checkpoint e destino divergente.
- Browser._group abre o destino, confirma URL e aguarda até 3 segundos pelo compositor. GROUP_COMPOSER_READY é só sinal de interface, não prova de permissão ou publicação.
- O próprio fluxo _publish confere o destino antes de abrir compositor.
- GET /api/group/current consulta URL observada, sem navegar.
- POST /api/group/open devolve estado, ID e operação auditável.
- Cadastro de grupos usa mesma trava da publicação e deduplica URLs canônicas.
- O painel diferencia grupo selecionado de grupo aberto.
- selected-account.json grava só ID local de perfil, sem cookies, e preserva a escolha após reinício.
- VIDEO_PROCESSING impede trocar de grupo enquanto visível.

## Gates locais para Antigravity
1. Preservar data/, Chrome e sessões. Não usar reset/force e não mesclar.
2. Testes Python/CI, /health.build_revision igual ao checkout.
3. Selecionar grupo autorizado A. Observar indicação "selecionado mas não aberto"; abrir A, validar ID/compositor no Chrome.
4. Selecionar grupo autorizado B, confirmar que o painel indica divergência até abrir B; verificar ID e compositor.
5. Simular offline redirecionamentos para login, checkpoint e grupo errado; sem clicar Publicar.
6. Enquanto houver VIDEO_PROCESSING, provar bloqueio de nova navegação.
7. Testar perfil secundário e persistência após reinício SOMENTE quando o servidor estiver inativo, sem copiar cookies.
8. Somente depois dos gates, pedir autorização para uma publicação real no grupo B e confirmar no feed. Não reenviar resultados incertos.
9. Relatar PASS/FAIL/NÃO TESTADO, IDs de operação e evidência verificada.

Limites: não existe confirmação automática de permalink, detecção integral da identidade Facebook, nem idempotência global entre operações. Não declarar pronto para agendamento de campanhas recorrentes.

Referências: https://playwright.dev/python/docs/navigations e https://playwright.dev/python/docs/actionability
