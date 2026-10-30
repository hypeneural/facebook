---
name: fase3-filechooser
description: Homologa correções P0 de janela Windows Abrir, múltiplas fotos, vídeo e diagnóstico de versão na branch de revisão sem perder sessões. Agente executa tudo salvo login e autorização da postagem.
---

# /fase3-filechooser — Antigravity Gemini 3.8 Flash

1. Preservar dados locais: `git status --short`; confirmar que `data/chrome-profile` e `data/profiles` continuam fora do Git. NÃO deletar perfil, cookies, fotos ou `data/`.
2. Fazer checkout da branch `fix/filechooser-media-preflight-forensic-20261030` sem reset/force, preservando trabalho local da PR #1.
3. Ler `AGENTS.md` e `docs/AUDITORIA_FILECHOOSER_20261030.md`; executar `/verificar-mvp` (CI offline).
4. **Não refazer automaticamente** as publicações reais que já foram feitas. Verificar no grupo o vídeo anterior, se possível reproduzindo um trecho depois da conclusão do processamento.
5. A janela nativa "Abrir" remanescente de uma tentativa antiga deve ser fechada uma única vez pelo controle **Cancelar** na própria janela. Não usar Alt+F4 universal nem pressionar ESC na página sem saber o foco.
6. Rodar `start-windows.ps1`. Se `STALE_SERVER`, consultar `/health` e `busy`; com `busy=false`, encerrar **apenas o PID do servidor deste projeto** após verificar sua linha de comando/working directory. Nunca matar Chrome, CRM, outros servidores ou processo ocupado. Reiniciar normalmente.
7. Conferir `build_revision` igual à revisão do Git, e que perfis e grupo salvo são os esperados.
8. Homologação sem publicar: abrir grupo, preparar 2/6 fotos e um vídeo de teste e verificar que o seletor nativo Windows não abre no caminho direto. **Se houver dúvida, não clicar Publicar.**
9. Para um teste real de 6 fotos e/ou um MP4, mostrar conta, grupo, legenda e nomes/quantidades de arquivos; pedir autorização explícita para cada clique. Observar `UPLOAD_ROUTE_SELECTED`, `FILES_ASSIGNED`, `MEDIA_PREVIEW_READY`, `CAPTION_RECHECK_PASSED` e `SUBMIT_INTENT`.
10. Vídeo: aguardar a conclusão do processamento no feed e reprodução normal. Não classificar `SUBMITTED_UNVERIFIED` como publicado por causa do clique ou spinner.
11. Se falha antes de `SUBMIT_INTENT`, registrar `operation_id`, estágio, erro, contagens e método do upload; corrigir uma hipótese de cada vez. Se marcador existe, nunca reenviar sem verificar no Facebook.
12. Entregar tabela PASS/FAIL/NÃO TESTADO com evidências locais redigidas, versão em execução e qualquer patch. Não fazer merge antes de homologação.

Sem features novas, APIs privadas, stealth, proxies, loop de postagens, automação para contornar bloqueios ou intervenção do operador no terminal.
