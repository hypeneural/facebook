# Dossiê Técnico de Homologação e Análise de Resiliência

> **Projeto:** Facebook Grupos MVP Local  
> **Repositório:** [https://github.com/hypeneural/facebook](https://github.com/hypeneural/facebook)  
> **Data da Homologação:** 29/10/2026  
> **Filosofia:** AI-First (Agente executa trabalho técnico integral; operador supervisiona e autoriza)

---

## 1. Resumo Executivo da Homologação

O MVP local do projeto foi homologado em ambiente real Windows com o Google Chrome oficial dedicado, atingindo com êxito todos os critérios de aceite estabelecidos em `AGENTS.md` e `docs/MVP_ACCEPTANCE.md`.

### Status dos Gates Oficiais

| Gate | Critério | Status | Evidência Real |
| :---: | :--- | :---: | :--- |
| **0** | `start-windows.ps1 -CheckOnly` | **PASS** | Python 3.12.10 oficial detectado; `.venv` criado com dependências instaladas. |
| **1** | `compileall` e `pytest` | **PASS** | 12 testes unitários offline aprovados (100% de sucesso). |
| **2** | `GET /health` responde `ok=true` | **PASS** | Servidor FastAPI/Uvicorn rodando localmente na porta 8108. |
| **3** | Chrome visível com perfil isolado | **PASS** | Navegador persistente em `data/chrome-profile`, sem interferir no Chrome pessoal. |
| **4** | Login detectado | **PASS** | Cookie `c_user` detectado com sucesso via `/api/session` (`logged_in: true`). |
| **5** | Grupo autorizado aberto | **PASS** | Grupo `https://www.facebook.com/groups/464027871072447/` aberto e acessível. |
| **6** | Foto local de teste anexada | **PASS** | Imagem real `1.png` (2,14 MB) anexada com prévia renderizada no compositor. |
| **7** | Autorização explícita prévia | **PASS** | Apresentada a prévia e solicitada autorização formal antes de cada clique externo. |
| **8** | Publicação real efetuada | **PASS** | Clique único executado com status `SUBMITTED_UNVERIFIED` e post confirmado no grupo. |

---

## 2. Arquitetura Atual do Projeto

```
gruposface/
├── app/
│   ├── browser.py         # Automação Playwright (thread dedicada, Chrome persistente, seletores)
│   ├── main.py            # API FastAPI local (127.0.0.1:8108), proteção de origem e histórico
│   ├── validation.py      # Sanitização estrita de URLs e validação de extensões/tamanhos
│   └── static/index.html  # Painel web local simples para operação humana
├── docs/
│   ├── ANTIGRAVITY.md     # Diretrizes de IA e modelos
│   ├── MVP_ACCEPTANCE.md  # Checklist formal de gates
│   └── DOSSIE_HOMOLOGACAO_E_RESILIENCIA.md # Este documento
├── scripts/
│   └── doctor.py          # Preflight offline sem rede
├── tests/                 # Testes unitários (sem acesso a rede ou Facebook real)
├── data/                  # Perfil persistente do Chrome, logs e histórico (ignorado pelo git)
├── AGENTS.md              # Regras permanentes de operação do agente AI
└── start-windows.ps1      # Bootstrap determinístico no Windows
```

---

## 3. Incidentes Reais em Produção & Correções Comprovadas

Durante a homologação ao vivo contra a interface web do Facebook (PT-BR), foram diagnosticados e solucionados dois problemas reais de automação:

### Incidente 1: Timeout no Seletor do Botão "Publicar"
- **Sintoma:** A API retornava `FAILED_BEFORE_SUBMIT` com mensagem de timeout (12s) procurando `get_by_role("dialog").last.get_by_role("button", name=POST_NAME).last`.
- **Causa Raiz:** Ao abrir o diálogo de criação de post, o Facebook frequentemente renderiza sub-elementos com `role="dialog"` (como menus de opções ou container de mídia). O código usava `.last`, buscando o botão no elemento filho errado, além de usar uma expressão regular rígida com âncoras `^...$`.
- **Correção Aplicada ([Commit e40ef74](https://github.com/hypeneural/facebook/commit/e40ef74)):**
  1. Criação da lista `POST_BUTTONS` cobrindo seletores de acessibilidade (`[role="dialog"] [role="button"][aria-label*="Publicar"]`, `div[role="button"]:has-text("Publicar")`, fallbacks em inglês e variações).
  2. Varredura determinística por todos os diálogos visíveis antes de fallback para a página geral.

### Incidente 2: Upload de Texto Puro sem a Imagem
- **Sintoma:** O post foi publicado no grupo com sucesso, mas continha apenas o texto da legenda, sem a foto `1.png`.
- **Causa Raiz:** A linha `self.page.locator('input[type="file"]').first` buscava no documento inteiro. Como a página do feed do grupo já continha outros inputs de arquivo em segundo plano (na área de comentários de posts anteriores), `fi.count()` retornava verdadeiro, pulando o clique no botão "Foto/vídeo" do compositor. O arquivo era setado no input errado e o formulário do post ficava sem mídia.
- **Correção Aplicada ([Commit 058d524](https://github.com/hypeneural/facebook/commit/058d524)):**
  1. Criação da lista `MEDIA_BUTTONS` para forçar a abertura da área de foto/vídeo no diálogo.
  2. Restrição estrita de busca de arquivo para `[role="dialog"] input[type="file"]`.
  3. **Trava de segurança:** Adicionada validação de prévia visual (`preview = self.page.locator('[role="dialog"] img[src*="blob:"], ...')`). Se o Facebook não renderizar a imagem na tela em até 12 segundos, a operação é abortada antes do clique de publicação, impedindo postagens acidentais sem foto.

---

## 4. Matriz de Fragilidades & Oportunidades de Resiliência

Para tornar o sistema ainda mais robusto em operações continuadas, identificamos os seguintes pontos de atenção técnica:

| Área | Cenário de Fragilidade | Sugestão de Melhoria de Resiliência |
| :--- | :--- | :--- |
| **Tipos de Grupo** | Grupos no modo "Compra e Venda" têm interface diferente ("O que você está vendendo?") em relação a grupos de discussão ("Escreva algo..."). | Ampliar `COMPOSERS` para suportar botões de grupos de classificados sem ativar formulários de venda obrigatórios. |
| **Upload de Vídeo** | Vídeos MP4/MOV passam por processamento e transcodificação no Facebook, levando de 15s a 2 minutos para habilitar o botão "Publicar". | Implementar timeout dinâmico na espera do botão publicar dependendo do tipo de mídia (imagem vs vídeo). |
| **Carrossel de Fotos** | Upload de até 10 fotos pode exigir tempo variável de renderização dos thumbnails. | Validar que a contagem de thumbnails gerados no DOM corresponde ao número de arquivos enviados. |
| **Mudanças de DOM** | O Facebook altera nomes de classes CSS e atributos com frequência. | Priorizar seletores semânticos baseados em acessibilidade (`aria-label`, `role`, texto visível normalizado sem case-sensitive). |
| **Sessão Expirada / Checkpoint** | O Facebook pode solicitar confirmação de segurança ou desconectar a conta. | Detectar telas de checkpoint/bloqueio temporário e retornar erro amigável imediato sem loops de tentativa. |
| **Proteção contra Duplicidade** | Em conexões lentas, um clique pode demorar para fechar o diálogo. | Manter a regra rígida de `SUBMITTED_UNVERIFIED`: se o clique foi emitido, **nunca** reenviar automaticamente. |

---

## 5. Prompt Estruturado para Validação no ChatGPT

Copie e cole o bloco abaixo no ChatGPT para solicitar a análise e propostas de código refinadas:

```markdown
Olá, ChatGPT!

Estou trabalhando no projeto "Facebook Grupos MVP", um sistema Python (Playwright + FastAPI) voltado para automação local e assistida de postagens em grupos do Facebook no Windows.

### Filosofia e Restrições Rígidas do Projeto (conforme AGENTS.md):
1. Escopo estrito: Uma conta, um grupo autorizado por vez, uma foto ou vídeo único, um clique de publicação.
2. Sem bibliotecas externas pesadas, sem APIs privadas do Facebook, sem proxies, sem múltiplos perfis simultâneos.
3. Não mascarar falhas: Se um clique pode ter ocorrido, o estado deve ser marcado como SUBMITTED_UNVERIFIED e nunca repetir automaticamente.
4. O navegador roda em modo visível com perfil persistente em `data/chrome-profile` (Chromium Playwright).

### Código Atual do Componente Crítico (`app/browser.py`):
```python
COMPOSERS=[
    '[role="button"][aria-label*="Escreva algo"]',
    '[role="button"][aria-label*="Escrever algo"]',
    '[role="button"][aria-label*="Criar publicação"]',
    '[role="button"][aria-label*="No que você está pensando"]',
    '[role="button"][aria-label*="Write something"]',
    'div[role="button"]:has-text("Escreva algo")',
    'div[role="button"]:has-text("Write something")',
    'div[role="button"]:has-text("O que você está pensando")',
]
EDITORS=['[role="dialog"] [contenteditable="true"][role="textbox"]','[role="dialog"] [data-lexical-editor="true"]','[role="dialog"] [contenteditable="true"]']
MEDIA_BUTTONS=[
    '[role="dialog"] [aria-label*="Foto/vídeo"]',
    '[role="dialog"] [aria-label*="Foto/video"]',
    '[role="dialog"] [aria-label*="Photo/video"]',
    '[role="dialog"] [aria-label*="Foto"]',
    '[role="dialog"] [aria-label*="Photo"]',
    '[role="dialog"] div[role="button"]:has-text("Foto/vídeo")',
    '[role="dialog"] div[role="button"]:has-text("Photo/video")',
    '[role="dialog"] div[role="button"]:has-text("Foto")',
]
POST_BUTTONS=[
    '[role="dialog"] [role="button"][aria-label*="Publicar"]',
    '[role="dialog"] div[role="button"]:has-text("Publicar")',
    '[role="dialog"] [role="button"][aria-label*="Post"]',
    '[role="dialog"] div[role="button"]:has-text("Post")',
    '[role="dialog"] [role="button"][aria-label*="Publish"]',
    '[role="dialog"] div[role="button"]:has-text("Publish")',
    '[role="dialog"] [role="button"][aria-label*="Compartilhar"]',
    '[role="dialog"] div[role="button"]:has-text("Compartilhar")',
    '[role="button"][aria-label*="Publicar"]',
    'div[role="button"]:has-text("Publicar")',
]
POST_NAME=re.compile(r"^(Publicar|Publicar agora|Publicar publicação|Post|Publish|Compartilhar|Share|Compartilhar agora)$",re.I)
```

E a lógica de envio em `_publish`:
```python
        clicked=False
        try:
            self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
            self.page.wait_for_timeout(1300)
            if "/groups/" not in self.page.url:raise ValueError("Facebook redirecionou; confira acesso.")
            composer=self._find(COMPOSERS)
            if composer is None:raise ValueError("Não encontrei campo de criação de publicação no grupo.")
            composer.click();self.page.wait_for_timeout(900)
            if caption:
                editor=self._find(EDITORS)
                if editor is None:raise ValueError("Não encontrei editor da legenda.")
                editor.fill(caption)
            if media:
                mb=self._find(MEDIA_BUTTONS)
                if mb is not None:
                    try:mb.click();self.page.wait_for_timeout(1000)
                    except Exception:pass
                fi=self.page.locator('[role="dialog"] input[type="file"]').last
                if not fi.count():
                    fi=self.page.locator('input[type="file"]').last
                fi.wait_for(state="attached",timeout=12000)
                fi.set_input_files(media,timeout=20000)
                self.page.wait_for_timeout(3000)
                preview=self.page.locator('[role="dialog"] img[src*="blob:"], [role="dialog"] img[src*="scontent"], [role="dialog"] [aria-label*="Remover"], [role="dialog"] [aria-label*="Editar"]').first
                try:preview.wait_for(state="visible",timeout=12000)
                except Exception:raise ValueError("Falha ao carregar prévia da mídia no Facebook.")
            btn=self._find(POST_BUTTONS)
            if btn is None:
                dialogs=self.page.get_by_role("dialog")
                for i in range(dialogs.count()):
                    d=dialogs.nth(i)
                    if d.is_visible():
                        b=d.get_by_role("button",name=POST_NAME)
                        if b.count() and b.last.is_visible():
                            btn=b.last;break
                if btn is None:
                    btn=self.page.get_by_role("button",name=POST_NAME).last
            btn.wait_for(state="visible",timeout=12000)
            clicked=True
            btn.click(timeout=120000 if media else 15000)
            self.page.wait_for_timeout(1900)
            pending=self.page.get_by_text(re.compile("aguardando aprovação|pending approval",re.I))
            return {"status":"PENDING_REVIEW" if pending.count() and pending.first.is_visible() else "SUBMITTED_UNVERIFIED","message":"Clique realizado. Verifique no grupo antes de tentar novamente.","group_url":url}
        except Exception as e:
            if clicked:return {"status":"SUBMITTED_UNVERIFIED","message":"O clique pode ter ocorrido; confira o grupo antes de outra tentativa.","group_url":url}
            raise ValueError("Falha antes de clicar Publicar: "+str(e)[:260]) from e
```

### O que preciso que você avalie:
1. **Resiliência a Mudanças de Layout:** Como tornar a detecção do compositor, do botão de foto e do botão publicar ainda mais imune a variações A/B test do Facebook PT-BR sem adicionar bibliotecas externas?
2. **Upload de Vídeo:** Como calibrar o timeout e a espera da renderização quando o upload for um vídeo (MP4) que exige codificação no Facebook?
3. **Carrossel de Imagens:** Caso enviemos até 10 imagens, como garantir que todas foram carregadas antes do clique?
4. **Tratamento de Exceções:** Algum seletor ou espera pode gerar falsos positivos ou falsos negativos?

Por favor, forneça sugestões de patches mínimos e cirúrgicos que mantenham a simplicidade e a conformidade com as regras do projeto.
```
