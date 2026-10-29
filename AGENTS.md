# Instruções canônicas para Antigravity 3.8 Flash
Objetivo MVP: abrir Chrome, login MANUAL Facebook, publicar UMA VEZ em UM grupo autorizado, legenda e mídia local.
NÃO criar SaaS, agendador, campanhas, múltiplas contas, scraping, bypass de restrições, CRM, VPS, nova arquitetura.
Ler README e .agent/workflows/mvp-local.md antes de executar. Stack: Python FastAPI + Playwright com perfil persistente data/chrome-profile.
Arquivos: app/main.py (API), app/browser.py (Playwright numa única thread), app/validation.py (regras), app/static/index.html (painel), run.py.
Nunca pedir, coletar, imprimir, commitar ou enviar senhas, cookies ou tokens. data/ fora do Git.
Proibido dizer POSTADO apenas com base em clique, teste unitário ou retorno HTTP. SUBMITTED_UNVERIFIED requer inspeção visual do grupo.
Se falhar o seletor PT-BR, inspecionar Chrome e corrigir só app/browser.py com evidência local. Não codificar feature nova.
Executar python -m compileall app run.py e python -m pytest -q; após isso UMA postagem real com aprovação explícita do operador.
Não tentar novamente se botão publicar já foi acionado e resultado é incerto.
