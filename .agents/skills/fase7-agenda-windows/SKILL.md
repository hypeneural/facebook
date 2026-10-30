---
name: fase7-agenda-windows
description: Homologação conservadora de uma agenda diária SQLite com rodízio editorial de posts permitidos, Windows Task Scheduler e logs, sem reenviar operações incertas.
---

# /fase7-agenda-windows

1. Conferir Git/PR #7 e ler AGENTS.md e docs/AUDITORIA_FORENSE_AGENDA_FASE7.md. Não resetar nem mesclar.
2. Rodar python -m compileall, doctor --offline, pytest e python scripts/verify_scope_safety.py --offline. Não declarar ambiente LIVE por teste offline.
3. Confirmar que o servidor tem build_revision correto e sessão Chrome interativa da conta especificada.
4. Manter data/ e perfis intactos. Criar data/daily.json a partir do exemplo, com enabled=false e sem allow_unattended.
5. Usar apenas grupos nos quais o conteúdo é permitido. Preencher pelo Antigravity textos e criativos aprovados pelo operador.
6. Configurar horários de Brasília 08:00, 10:00, 16:00, 18:00, 22:00, ou os horários que operador fornecer.
7. Executar python scripts/daily_tick.py SEM --execute; verificar o planejamento do banco SQLite e a distribuição aleatória reproduzível.
8. Simular reboot, timeout, resposta 500, conta errada, arquivo removido, configuração alterada e computador que acorda depois de 20min; nenhuma falha pode gerar retry pós-clique.
9. Verificar scripts/check_dialogs.py e verify_scope_safety.py: erros Win32 e health incorreto devem falhar, jamais PASS silencioso.
10. Rodar powershell -File scripts/install_windows_scheduler.ps1 sem -Install, apenas preview.
11. Antes de qualquer publicação REAL, mostrar grupo, conta, mídia, texto e solicitar autorização explícita.
12. Não instalar Task Scheduler nem mudar enabled/allow_unattended sem aprovação adicional do operador.
13. Após canário único, exigir evidência real no Facebook; marcar VERIFIED_EXTERNALLY só se observada; caso contrário manter NEEDS_REVIEW.
14. Reportar commit, CI, jobs, status e evidências. Não introduzir proxy, stealth, bypass de bloqueios, chamadas GraphQL privadas ou envio em massa não autorizado.

## Critério de GO
GO offline/preview quando testes passam. NO-GO campanha diária totalmente autônoma se o estado pós-clique continuar apenas SUBMITTED_UNVERIFIED.
