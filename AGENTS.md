# Facebook Grupos — Antigravity / Gemini 3.8 Flash

## Fonte da verdade
A `main` tem o MVP homologado para **uma foto** conforme capturas do operador. A branch `audit/media-resilience-groups-profiles-20261029` é uma **PR draft**, ainda NÃO homologada para vídeo, várias fotos ou segunda conta. O CI só valida offline. **Não declarar a fase 2 pronta para uso real antes dos testes.**

## Escopo exato da fase 2
O agente executa ambiente, testes e diagnóstico, e opera uma postagem por vez com autorização explícita:
1. Escolher um **grupo salvo** para abrir/publicar. NÃO postar em todos os grupos de uma só vez.
2. Selecionar um **perfil Facebook local** (somente um ativo). Login humano no site; não compartilhar/exportar cookies.
3. Publicar 2 fotos, depois eventualmente 6–10 fotos ou um vídeo MP4, **em execuções distintas e autorizadas**.
4. Preservar `data/chrome-profile` da conta principal. Outros perfis em `data/profiles/<id>`.
5. Se a prévia de mídia não comprovar a quantidade, falhar antes do clique. Se o botão PODE ter sido clicado: `SUBMITTED_UNVERIFIED` e nenhuma repetição automática.

## Arquitetura que não deve ser modificada sem evidência
- `app/browser.py`: Playwright na mesma thread, seletores e envio.
- `app/media_policy.py`: orçamentos de espera e validação offline de mídia.
- `app/main.py`: API local e upload temporário.
- `app/validation.py`: URL Facebook e extensão de mídia.
- `app/static/index.html`: painel simples em português.
- `start-windows.ps1`: instalação e start no Windows.
- `data/`: sessão, perfis, arquivos e logs locais; **NUNCA versionar**.

## Agent Skills
- `.agents/skills/mvp-local/SKILL.md`: base homologada para foto única.
- `.agents/skills/verificar-mvp/SKILL.md`: testes offline.
- `.agents/skills/diagnosticar-publicacao/SKILL.md`: diagnóstico de erro real.
- `.agents/skills/fase2-validar/SKILL.md`: validação progressiva de mídia, grupos e perfis desta PR.

## Regras anti-alucinação
- Ler `git status --short`, `git branch --show-current`, este arquivo e a skill **antes** de executar.
- Não editar main, não fazer merge, não apagar sessões locais, não usar APIs privadas do Facebook, não contornar CAPTCHA/bloqueios.
- Operador apenas supervisiona; credenciais/2FA são inseridas **diretamente** no Facebook.
- Não fazer login/alterar conta durante upload/postagem em andamento.
- Cada teste real exige grupo autorizado, prévia e autorização do operador.
- Falha antes do clique: inspecionar o DOM real e fazer correção mínima. Resultado incerto: **parar e conferir o grupo**, não repetir.
- Playwright tem `chromium_sandbox=False` por padrão. Investigar aviso `--no-sandbox` em sessão de teste isolada; não alterar comandos do Chrome cegamente nem sobrescrever o perfil principal.
- Proibido criar agenda, campanhas em massa, rotação, proxies, CRM, VPS ou outras integrações nesta fase.
- Relatório final com PASS/FAIL, evidências por mídia/conta/grupo, links reais somente se observados.

## Telemetria e diagnóstico P1
Cada tentativa recebe `operation_id` estável correlacionando browser, API, `data/operations.jsonl` e histórico. Durante execução abrir `GET /api/operations`. **Nunca incluir legenda, nome de foto, path, cookie ou DOM nos logs.** Se `SUBMIT_INTENT` existir, qualquer falha posterior é de resultado INCERTO, não retry automático. Ler `docs/AUDITORIA_RESILIENCIA_P1.md` e realizar `/fase2-validar`.

## Hotfix de revisão independente (30/10/2026)
Na branch `fix/filechooser-media-preflight-forensic-20261030` executar a skill `/fase3-filechooser`. O motivo é o seletor nativo **Abrir** persistente após envio. Nunca misturar clique no botão Foto/vídeo com `set_input_files` do mesmo envio. Preferir input direto; usar `expect_file_chooser + set_files` somente se dinâmico. Colagens exigem prova quantitativa; botão "Editar tudo" NÃO basta. `/health.build_revision` deve corresponder ao Git local. Não mesclar sem validação real.

## Fase 7 — Agenda local (nova PR independente)

A proibição de agenda nas Fases 2–6 permanece histórica para aquelas fases. A Fase 7 é definida em docs/AUDITORIA_FORENSE_AGENDA_FASE7.md e na skill /fase7-agenda-windows. Permite somente grupos explicitamente autorizados, agenda SQLite auditável e escolha de variações editoriais aprovadas. Não ativar enabled/allow_unattended ou instalar Task Scheduler sem homologação local e autorização do operador. Resultado incerto bloqueia novos disparos até verificação; não remover proteção por conveniência.
