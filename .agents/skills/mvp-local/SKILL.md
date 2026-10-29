---
name: mvp-local
description: Executa sozinho o setup e a primeira homologação do Facebook Grupos MVP no Windows via Antigravity Gemini 3.8 Flash; prepara Python/Chrome, abre servidor local e valida uma publicação em grupo autorizado.
---

# /mvp-local — ordem determinística

Objetivo: operador observa e autoriza; agente executa comandos, janelas e diagnóstico.

1. Abrir workspace. Se ausente, clonar https://github.com/hypeneural/facebook.git. Se já clonado, fazer git status --short e preservar qualquer edição local.
2. Ler AGENTS.md; não instalar projetos externos. Executar na raiz:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1 -CheckOnly
3. Se PYTHON_MISSING, instalar Python 3.12 oficial (preferir winget Python.Python.3.12), reabrir terminal e repetir UMA vez; não mandar o operador instalar.
4. Rodar dependências de teste (somente se necessárias), compileall e pytest como a habilidade /verificar-mvp.
5. Executar:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1
   Aguardar PASS /health. O script abre painel HTTP local.
6. Pelo painel ou interface da máquina, clicar Abrir Chrome. Perfil independente em data/chrome-profile. Se sessão não estiver autenticada, permitir que o operador autentique DIRETAMENTE no Facebook. Nunca solicitar senha no chat.
7. Conferir login. Escolher um grupo onde o operador esteja autorizado a publicar, abrir o grupo, preparar legenda curta e UMA imagem de teste não privada. Não coletar dados de clientes.
8. Mostrar ao operador grupo exato, legenda e arquivo. Solicitar autorização explícita para o primeiro clique externo. Somente então clicar Publicar UMA vez.
9. Conferir página do grupo: post visível/link real ou pendente de moderação. Se SUBMITTED_UNVERIFIED, não repetir; aguardar verificação.
10. Relatar cada gate como PASS/FAIL/NÃO TESTADO. Nunca declarar postagem real com base somente no CI.

Diagnóstico rígido: PYTHON_MISSING -> Python; PIP_FAILED -> conectividade/pacote; BROWSER_MISSING -> Playwright Chromium; SERVER_START_FAILED -> data/server-stderr.log; compositor não encontrado -> /diagnosticar-publicacao. Uma correção por sintoma. Não avançar para campanhas ou agendamentos.
