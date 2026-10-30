# Facebook Grupos — instruções permanentes para Antigravity 2.0 / Gemini 3.8 Flash

## Objetivo atual (AI-first)
O agente cuida de clonagem, ambiente, testes, inicialização, interface e diagnóstico; o operador apenas supervisiona. A autenticação pessoal/2FA do Facebook e a autorização explícita de publicação real continuam sob controle do operador.

**Escopo:** uma conta, um grupo autorizado, uma foto local de teste e um único clique de publicação. Vídeo único opcional depois. NÃO implementar nesta etapa agendamento, campanhas, múltiplas contas, rotação, integrações, API privada do Facebook ou contorno de restrições.

## Arquivos reais
- app/browser.py: browser Playwright visível, Chrome persistente, seletores PT-BR.
- app/main.py: API local 127.0.0.1:8108, upload temporário e histórico.
- app/validation.py: URL e tipos de mídia.
- app/static/index.html: painel local.
- start-windows.ps1: bootstrap e inicialização idempotente.
- scripts/doctor.py: preflight offline.
- tests/: testes sem Facebook real.
- data/: perfil/cookies locais, anexos e logs; **NUNCA commitar, enviar ou ler os cookies**.

## Habilidades oficiais (substituem workflows legados)
- .agents/skills/mvp-local/SKILL.md — /mvp-local: instalar, iniciar, validar login e um post.
- .agents/skills/verificar-mvp/SKILL.md — /verificar-mvp: checagens offline.
- .agents/skills/diagnosticar-publicacao/SKILL.md — /diagnosticar-publicacao: corrigir apenas erro comprovado.

Antigravity deixou de indexar workflows antigos em 19/10/2026. Não usar .agent/workflows nem pedir ao operador comandos manuais. Skills usam frontmatter name/description.

## Regras para evitar alucinações
1. Primeiro ler os arquivos reais; não inventar endpoints, pacotes ou recursos não presentes.
2. Preferir Gemini 3.8 Flash em Medium; usar High só em diagnóstico técnico difícil.
3. Seguir 1 sintoma -> 1 hipótese verificada -> patch mínimo -> teste relevante. Sem refatorações, novos frameworks ou loops de testes.
4. CI verde NÃO comprova postagem no Facebook; o estado SUBMITTED_UNVERIFIED exige inspeção no grupo.
5. Nunca repetir postagem automaticamente se um clique pode ter ocorrido, mesmo se Playwright retornar timeout.
6. Não pedir senha, exportação de cookies, token, screenshots com dados privados ou edição manual de código.
7. NUNCA clicar Publicar sem aprovação explícita do operador para aquele grupo e conteúdo.
8. Se o Facebook exigir CAPTCHA, login, aprovação ou bloquear ações, parar e reportar; não contornar.
9. Não tocar em sistemas do CRM, VPS, ChromeWa ou instalações fora deste projeto.
10. Final: reportar evidência por gate: Python, dependências, testes, servidor, Chrome, login, grupo, foto, clique e confirmação externa. Não inventar permalink.

## Fase seguinte — troca assistida de grupos e perfis
Esta branch de auditoria permite múltiplos grupos SALVOS e perfis locais distintos, mas **não execução simultânea ou automática**. Operador autoriza cada publicação. Use a documentação em docs/FASE2_AUDITORIA.md. Não editar dados de sessão, não copiar cookies entre perfis. Antes de merge, homologar fotos múltiplas e vídeo separadamente.
