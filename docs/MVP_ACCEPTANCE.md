# Checklist de homologação MVP
| Gate | Evidência requerida |
|---|---|
| 0 | start-windows.ps1 -CheckOnly PASS |
| 1 | compileall e pytest PASS |
| 2 | /health responde ok=true |
| 3 | Chrome visível com perfil isolado |
| 4 | Login detectado (sem exportação de cookies) |
| 5 | URL /groups/ autorizada e compositor visível |
| 6 | Uma foto local de teste anexada |
| 7 | Autorização explícita antes de clicar Publicar |
| 8 | Publicação real confirmada visualmente, link real ou aprovação pendente |

SUBMITTED_UNVERIFIED = pode ter sido enviado, NÃO reenviar sem verificar.
FAILED_BEFORE_SUBMIT = falha antes do clique reconhecido pelo programa.
PENDING_REVIEW = aviso de aprovação, publicação ainda não visível ao público.

Até o gate 8 passar no computador autenticado, o MVP não está homologado em produção.
