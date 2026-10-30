---
name: fase2-validar
description: Homologa por etapas a PR Draft de fotos múltiplas, vídeo MP4 e troca sequencial de grupos e perfis Chrome do Facebook Grupos MVP. Usar no Windows, sem disparo em massa ou alteração de conta sem autorização.
---

# /fase2-validar — roteiro para Antigravity 3.8 Flash

1. Confirmar branch `audit/media-resilience-groups-profiles-20261029`; se ainda estiver na `main`, fazer checkout da branch **preservando alterações locais**, sem reset ou force. Não mesclar a PR.
2. Executar `/verificar-mvp` uma vez (compileall, doctor e pytest). Não inventar falhas após PASS.
3. Iniciar `start-windows.ps1`, abrir o painel; confirmar que a conta **principal** ainda utiliza `data/chrome-profile` e permanece autenticada.
4. Cadastro de grupo: salvar outro grupo em que o operador esteja autorizado; selecionar e abrir. Validar URL e compositor sem publicar. Nunca publicar automaticamente em lista.
5. Cadastro de conta: criar alias de perfil local (ex. `Conta 2`), selecionar, verificar nova pasta `data/profiles/<id>`; autenticação/2FA exclusivamente na janela do Facebook pelo operador. Voltar à conta principal e comprovar que o login original permanece. Nunca copiar cookies.
6. **Duas fotos:** mostrar nomes e legenda; autorização explícita; verificar `input.files`, 2 prévias e botão habilitado antes de qualquer clique. Se a contagem de prévias não refletir o Facebook real, **não clicar**, registrar DOM redigido e corrigir apenas o seletor necessário.
7. **Seis a dez fotos:** testar apenas depois do PASS com duas, em operação separada e com nova autorização. Registrar no feed cada imagem esperada.
8. **Um vídeo curto MP4:** aguardar miniatura/preview e botão habilitar até orçamento de 4 min. Isso não é prova definitiva de processamento no servidor. Conferir vídeo visível no grupo após o clique, com autorização explícita. Não usar vídeos privados de clientes.
9. Se Playwright acusar timeout após POSSÍVEL clique, o status é `SUBMITTED_UNVERIFIED`. Consultar `data/attempts.jsonl` somente metadados sem tokens; verificar o grupo antes de qualquer nova postagem.
10. Testar sandbox do Chromium em **perfil de teste**: avaliar `chromium_sandbox=True` conforme documentação Playwright; não alterar flag/args em produção sem teste e não adicionar `--no-sandbox` manualmente.
11. Fornecer relatório em tabela por gate com PASS, FAIL ou NÃO TESTADO. Não fazer merge enquanto vídeo, duas fotos e troca de conta não passarem.

Se falhar algum passo: 1 hipótese, 1 patch cirúrgico, 1 teste afetado e um CI final. Evitar testes infinitos e scripts novos.
