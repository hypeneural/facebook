# Facebook Grupos — MVP Local v0.1

**Objetivo:** validar login manual no Chrome e **uma publicação real por vez** em grupo de teste autorizado, com legenda e fotos OU vídeo armazenado no computador. Sem SaaS, tokens, CRM ou infraestrutura VPS. Código original enxuto: FastAPI + Playwright + Chrome persistente.

> **Estado:** código publicado, ainda **não homologado com Facebook real**. Não declarar postagem bem-sucedida sem verificar no grupo. O resultado `SUBMITTED_UNVERIFIED` significa apenas que o clique foi executado.

## Instalação no Windows 11 (Antigravity)

```powershell
git clone https://github.com/hypeneural/facebook.git
cd facebook
powershell -ExecutionPolicy Bypass -File .\start-windows.ps1
```

O painel abre em http://127.0.0.1:8108.

Se Chrome não estiver disponível e não houver Playwright Chromium:
```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```
Depois execute `start-windows.ps1` novamente.

## Primeira prova real
1. Clicar **Abrir Chrome**; fazer login no Facebook **diretamente na janela Chrome**.
2. Clicar **Conferir login**; não inserir senha no painel.
3. Informar a URL `https://www.facebook.com/groups/ID/` de um grupo de teste autorizado; clicar **Abrir grupo**.
4. Selecionar legenda curta e **uma imagem JPG de teste** (sem dados privados).
5. Confirmar **Publicar UMA VEZ** e observar o Chrome. Verificar no grupo e registrar eventual URL real.
6. Se falhar o seletor, corrigir **somente** `app/browser.py` segundo o elemento real observado; não refatorar arquitetura.
7. Nunca repetir automaticamente uma operação cujo clique possa ter ocorrido.

## Componentes
- `app/main.py`: painel web, controle de origem local, upload temporário e histórico.
- `app/browser.py`: navegador visível Playwright com perfil persistente (`data/chrome-profile`).
- `app/validation.py`: valida grupo HTTPS, arquivos, limites e legenda.
- `app/static/index.html`: interface simples em português.
- `start-windows.ps1`: ambiente Python e inicialização Windows.
- `AGENTS.md` e `.agent/workflows/mvp-local.md`: instruções estritas para Antigravity 3.8 Flash.
- `tests/`: testes offline. `.github/workflows/ci.yml`: CI Windows.

## Validação offline
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compileall app run.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Restrições do MVP
Apenas **um grupo por envio**; sem agendamentos, campanhas recorrentes, múltiplas contas, rotação, contorno de CAPTCHA, proxies ou envios em massa. Publicar em grupos que autorizam o conteúdo e respeitar suas regras. Automação da interface pode falhar após atualizações do Facebook.

**Dados locais:** `data/` não entra no Git (Chrome profile e histórico podem conter dados privados). Arquivos de upload temporários são eliminados depois da tentativa.

## Por que não portar FBKit inteiro?
O repositório público `hthmkt12/flowkit` tem um motor interessante, mas exige correções para executar ações reais e oferece um painel atrelado a rotas externas. Este MVP usa somente mecanismos gratuitos de navegador local e separa a prova de publicação das melhorias futuras.
