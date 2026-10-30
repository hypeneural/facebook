---
name: fase8-producao-grupos
description: Homologa 4 grupos com 3 por janela às 08 12 18 20h, incluindo migração SQLite, logs e Windows Scheduler, sem publicar conteúdo incerto outra vez.
---

# /fase8-producao-grupos (Antigravity 3.8 Flash)

A ordem abaixo é OBRIGATÓRIA. Não reescrever arquiteturas nem supor PASS sem prova.

1. Ler AGENTS.md, docs/AUDITORIA_FORENSE_PRODUCAO_FASE8.md e PR #8. Conferir status Git, sem reset/force/merge. Preservar pasta data/.
2. Antes de abrir Chrome, examinar /health, versão HEAD, busy=false e o último job no SQLite. Se houver NEEDS_REVIEW, não disparar.
3. Executar CI/pytest, python scripts/verify_scope_safety.py --offline; não classificar como LIVE.
4. Fazer backup SQLite transacional com sqlite3.backup(), não copiar cegamente arquivo WAL aberto. Guardar fora do repositório.
5. Usar banco de teste SEPARADO para validar migração jobs legada -> jobs_v2, preservando operações e conciliações.
6. Preparar data/daily.json a partir do exemplo Fase 8, com URLs reais de até 4 grupos autorizados e arquivos existentes no Windows. Começar enabled=false, allow_unattended=false.
7. Verificar com operador se são três grupos POR HORÁRIO (até 12/dia) ou três grupos NO DIA (até 3/dia). Não presumir alta frequência.
8. Testar 08:00, 12:00, 18:00 e 20:00 (America/Sao_Paulo), offsets 0/10/20 minutos, distribuição de grupos, limite por grupo e conteúdo escolhido.
9. Executar preview com banco de teste/data futura; não utilizar o banco vivo se a config tiver placeholders ou faltar mídia.
10. Validar troca real de Grupo A -> Grupo B apenas navegando, sem publicar; verificar conta e destino antes de qualquer clique.
11. Validar galeria com múltiplas fotos e vídeo em testes isolados pré-clique, sem spam de canários; nunca assumir sucesso com POST_UI_CLOSED_UNVERIFIED.
12. Testar janela Win32 de upload, falhas de mídia e estado de publicação pendente. Confirmar ausência de duplicações ao reiniciar.
13. Abrir painel /api/schedule e confirmar logs de jobs/operations.
14. Rodar preview do script PowerShell; verificar timezone Windows e contagem de tarefas. Não usar -Install sem autorização operacional.
15. Somente após autorizados grupos e mídia, executar no máximo UM canário, confirmar permalink e mídia visível. Reconciliar manualmente com evidência; se incerto, NEEDS_REVIEW.
16. Apresentar matriz de gates, evidência por arquivo, commits e conclusão GO/NO-GO. NÃO modificar main sem instrução explícita.

NUNCA inserir logins/cookies em Git, usar proxies/stealth, contornar checkpoints, instalar tarefas escondidas, desativar NEEDS_REVIEW, ou repetir post após clique incerto.
