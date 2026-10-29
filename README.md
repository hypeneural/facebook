# Facebook Grupos — MVP local AI-first

[Repositório](https://github.com/hypeneural/facebook) · Python/FastAPI/Playwright · Windows 11 · Sem assinatura ou SaaS.

**Status:** base de código + testes offline; **publicação real ainda não homologada**. MVP atual = uma foto em um grupo autorizado, com um único clique e inspeção do resultado.

## Para o Antigravity 2.0 — Gemini 3.8 Flash

Abra este repositório como workspace e chame **/mvp-local**. O agente faz instalação, diagnóstico, inicialização e navegação. Operador supervisiona, autentica a conta pessoal no Facebook se necessário e autoriza o clique da primeira publicação real.

- [Regras do projeto](AGENTS.md)
- [Skill de execução](.agents/skills/mvp-local/SKILL.md)
- [Skill de validação](.agents/skills/verificar-mvp/SKILL.md)
- [Skill de diagnóstico](.agents/skills/diagnosticar-publicacao/SKILL.md)
- [Documentação oficial e decisão técnica](docs/ANTIGRAVITY.md)
- [Critérios de aceite](docs/MVP_ACCEPTANCE.md)

Os workflows antigos em .agent/workflows deixaram de ser suportados em 19/10/2026. O projeto usa .agents/skills e regras AGENTS.md.

## Comandos prontos para o agente (não para o operador)

~~~powershell
git clone https://github.com/hypeneural/facebook.git
cd facebook
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1 -CheckOnly
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1
~~~

O bootstrap prepara .venv, evita reinstalações repetidas, instala Chromium apenas na ausência de Chrome, espera /health ficar pronto e abre o painel. URL: **http://127.0.0.1:8108/**

No painel: Abrir Chrome -> login diretamente na janela de Facebook -> conferir login -> grupo autorizado -> selecionar UMA foto local -> obter autorização -> Publicar UMA vez -> confirmar visualmente.

Comandos de verificação offline:
~~~powershell
.\.venv\Scripts\python.exe scripts/doctor.py --offline
.\.venv\Scripts\python.exe -m compileall -q app run.py scripts
.\.venv\Scripts\python.exe -m pytest -q
~~~

**Nunca publicar novamente automaticamente** após SUBMITTED_UNVERIFIED; não compartilhar data/ (sessões, cookies, mídias, logs). O navegador usa perfil separado em data/chrome-profile, conforme Playwright oficial. Sem contorno de restrições Facebook, sem campanhas múltiplas e sem agendamentos nesta etapa.
