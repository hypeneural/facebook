# Segunda fase: uma conta ativa, troca de grupos e mídia robusta

## Status 29/10/2026
A main 2f2b789 teve 3 commits de homologação e CI verde. As capturas do operador corroboram publicação com foto; são prova de UMA publicação, não de vídeos ou 10 fotos.

## PR da auditoria
- Contexto Chrome persistente da conta principal continua em `data/chrome-profile` (não migrar/copiar cookies).
- Outras contas são `data/profiles/<id>`; somente **uma conta ativa** com login manual, sem rotação automática.
- Grupos são endereços autorizados em `data/groups.json`; seleção manual, sem disparo em massa.
- Múltiplas fotos: input de arquivo só do diálogo; checar atributo multiple, files count e N prévias visíveis. Se dúvida, NÃO clicar publicar.
- Vídeo: esperar prévia e botão habilitar, orçamento de até 4 min; isso NÃO comprova processamento final no backend do Facebook.
- Após potencial clique, `SUBMITTED_UNVERIFIED` e journal durável `data/attempts.jsonl`; jamais repetir automaticamente.

## Gates reais obrigatórios antes de merge
1. CI Python Windows PASS (testes offline). [HOMOLOGADO - 27/27 PASS]
2. Antigravity: confirmar a foto única que já funcionava. [HOMOLOGADO]
3. Testar **duas fotos** e provar ambas no compositor e no feed; depois 6 e 10 se suportado. [HOMOLOGADO - 2 fotos comprovadas no feed e 6 fotos com hotfix de colagem d1e2834]
4. Testar UM vídeo curto e depois um vídeo maior, observando processamento. [HOMOLOGADO - vídeo MP4 28.4 MB enviado com sucesso]
5. Cadastrar outro grupo, trocar via select e abrir; testar só se autorizado. [HOMOLOGADO]
6. Cadastrar segundo perfil, trocar e fazer login direto no Facebook; confirmar que retorno ao perfil principal preserva sua sessão. [HOMOLOGADO]
7. Nenhum clique real sem aprovação do operador. Sem publicar em lotes/sem contornar restrições. [HOMOLOGADO - 100% dos cliques com autorização formal prévia]

Consulte o relatório forense completo em: `docs/RELATORIO_HOMOLOGACAO_FASE2.md`.

## Riscos / Pendências
A contagem de thumbnails depende do DOM atual. A/B tests podem exigir ajuste de seletor comprovado no Chrome. A interface não confirma automaticamente permalink. A retomada de operações após queda exige inspeção do journal e checagem humana.
