---
name: fase9-logs-windows
description: Homologa logs duráveis e snapshots sanitizados para auditoria via GitHub no Windows 11, sem expor cookies/DOM e sem publicações de teste não autorizadas.
---

# /fase9-logs-windows — roteiro Antigravity 3.8 Flash

1. Conferir branch audit/forensic-observability-windows-20261030, HEAD, CI e worktree. Não mexer no histórico de data/ e não fazer merge.
2. Ler docs/AUDITORIA_FORENSE_WINDOWS_FASE9.md e AGENTS.md.
3. Rodar compilação, pytest, doctor offline e verificar_scope --offline. Não chamar de prova LIVE.
4. Testar com eventos sintéticos job_id → REQUEST_ACCEPTED → operation_id. Se a rede cair após upload, verificar persistência da associação em operations.jsonl.
5. Rodar scripts/tick_observed.py SEM --execute e com config local desativado; deve produzir tick START/END e um JSON em reports/forensic/ (sem post).
6. Coletar eventos Windows PowerShell com scripts/collect_windows_diagnostics.ps1. Verificar tarefa, Task Scheduler Operational, error codes e ausência de texto bruto.
7. Executar scripts/export_forensics.py e checar schema, ids, horas e sanitização de segredo em logs de teste. Não subir data/, perfil, arquivos de mídia ou .env.
8. Rodar scripts/publish_forensic_report.ps1 SEM -Commit/-Push (PREVIEW). Só enviar o snapshot sanitizado após autorização; o script não deve adicionar outros arquivos.
9. Pré-visualizar scripts/install_forensic_sync.ps1, sem -Install. Instalação sincronização é separada do agendamento Facebook, opt-in.
10. Simular crash tick, Falha Task Scheduler, EVENT_LOG bloqueado, Git push sem conexão e retomada com NEEDS_REVIEW; não fazer retry automático de publicação.
11. Reportar PASS/FAIL/NÃO TESTADO por gate, versão local do servidor e arquivo JSON do snapshot no GitHub; não inventar permalink.
12. Nenhum merge e nenhuma mudança de flags enabled/allow_unattended sem autorização do operador.

Use correções mínimas se testes demonstrarem erro. Não iniciar loops de 50 testes live. Mantenha logs completos no computador; somente snapshots sanitizados vão ao GitHub.
