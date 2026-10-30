# Relatórios forenses versionáveis

Esta pasta contém **somente snapshots sanitizados** produzidos por `scripts/export_forensics.py`. Nenhum relatório real foi fabricado durante o desenvolvimento. Os primeiros arquivos `YYYY-MM-DD.json` aparecerão quando o Antigravity executar a coleta no Windows.

- Fonte local: `data/daily-queue.sqlite`, `data/operations.jsonl`, `data/diagnostics/ticks.jsonl`, `data/diagnostics/windows.json`.
- Dados brutos, cookies, arquivos, legendas, DOM, capturas de tela e perfis do Facebook nunca entram neste diretório.
- Snapshot: `python scripts/export_forensics.py`. Validar: `python scripts/validate_report_directory.py`.
- Prévia de envio: `powershell -File scripts/publish_forensic_report.ps1`. Para enviar o JSON sob autorização: `powershell -File scripts/publish_forensic_report.ps1 -Commit -Push`.
- Diagnóstico do Windows: `powershell -File scripts/collect_windows_diagnostics.ps1`.
- Sincronização opcional somente dos relatórios: `powershell -File scripts/install_forensic_sync.ps1` (prévia), ou `-Install` após validação. Não publica no Facebook.
- Backup completo **somente local**, ignorado no Git: `python scripts/backup_forensics.py`.

Campos de correlação: `run_id`, `job_id`, `operation_id`, `stage`, `at`, `error_code`, `error_class`, `source_file`, `source_line` e códigos de resultado do Windows.

**Atenção:** `SUBMITTED_UNVERIFIED` e `POST_UI_CLOSED_UNVERIFIED` não comprovam post no grupo. Para essa prova ainda é necessário conferência externa/permalink. Consulte `docs/AUDITORIA_FORENSE_WINDOWS_FASE9.md`.
