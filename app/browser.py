"""Playwright na mesma thread, perfil Chrome persistente; uma tentativa por operação."""
import asyncio
import re
import json
import os
import uuid
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.validation import group_url
from app.media_policy import media_kind, wait_budget_ms, remaining_budget_ms, input_file_count
from app.media_checks import pick_file_input_index, gallery_complete, caption_matches
from app.telemetry import error_code

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
class Browser:
    def __init__(self,root):
        self.default_root=Path(root)
        self.root=self.default_root
        self.data_dir=self.default_root.parent
        self.account_id="principal"
        self.pool=ThreadPoolExecutor(max_workers=1)
        self.pw=None
        self.ctx=None
        self.page=None
        self.audit=None
        self.last_submission=None

    def _emit(self,op_id,stage,**fields):
        if self.audit is not None and op_id:
            self.audit.emit(op_id,stage,account_id=self.account_id,**fields)

    def _accounts_file(self):
        return self.data_dir/"accounts.json"

    def _accounts(self):
        path=self._accounts_file()
        stored=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        if not isinstance(stored,list):
            raise ValueError("Arquivo de contas inválido.")
        return {"active":self.account_id,"accounts":[{"id":"principal","name":"Conta principal"}]+stored}

    def _add_account(self,name):
        name=str(name).strip()
        if not name or len(name)>70:
            raise ValueError("Informe um nome de 1 a 70 caracteres para o perfil.")
        data=self._accounts()["accounts"][1:]
        if len(data)>=10:
            raise ValueError("Limite de 10 perfis locais.")
        item={"id":uuid.uuid4().hex[:12],"name":name}
        data.append(item)
        self.data_dir.mkdir(parents=True,exist_ok=True)
        target=self._accounts_file()
        tmp=target.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,target)
        return {"created":item,"active":self.account_id}

    def _select_account(self,account_id):
        accounts=self._accounts()["accounts"]
        if account_id not in [a["id"] for a in accounts]:
            raise ValueError("Perfil local não cadastrado.")
        if account_id==self.account_id:
            return {"active":self.account_id,**self._open()}
        previous_id,previous_root=self.account_id,self.root
        self._close()
        self.account_id=account_id
        self.root=(self.default_root if account_id=="principal" else self.data_dir/"profiles"/account_id)
        try:
            result=self._open()
        except Exception:
            self.account_id,self.root=previous_id,previous_root
            # Restore metadata only. Never silently retry login or open Chrome.
            raise
        return {"active":self.account_id,**result}
    async def run(self,name,*args):
        loop=asyncio.get_running_loop()
        return await loop.run_in_executor(self.pool,lambda:getattr(self,"_"+name)(*args))
    def _open(self):
        if self.ctx:
            if not self.page or self.page.is_closed():
                self.page=next((p for p in self.ctx.pages if not p.is_closed()),None)
            if self.page:
                self.page.bring_to_front()
                return {"message":"Chrome já aberto."}
            self._close()
        from playwright.sync_api import sync_playwright
        self.root.mkdir(parents=True,exist_ok=True)
        self.pw=sync_playwright().start()
        try:
            options = {"headless": False, "viewport": {"width": 1360, "height": 900}, "locale": "pt-BR"}
            try:
                self.ctx=self.pw.chromium.launch_persistent_context(str(self.root),channel="chrome",**options)
            except Exception as chrome_error:
                # Apenas ausencia do executavel permite fallback. Nao mascara perfil em uso.
                if "executable doesn't exist" not in str(chrome_error).lower():
                    raise RuntimeError("Chrome não abriu. Confira se o perfil local já está em uso.") from chrome_error
                self.ctx=self.pw.chromium.launch_persistent_context(str(self.root),**options)
            self.page=self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
            self.page.goto("https://www.facebook.com/",wait_until="domcontentloaded",timeout=45000)
        except Exception:
            self._close();raise
        return {"message":"Chrome aberto. Entre manualmente no Facebook nessa janela."}
    def _status(self):
        if not self.ctx or not self.page or self.page.is_closed():return {"logged_in":False,"account_id":self.account_id,"message":"Abra o Chrome."}
        try: valid=any(c["name"]=="c_user" and c["value"] for c in self.ctx.cookies("https://www.facebook.com/"))
        except Exception:valid=False
        return {"logged_in":bool(valid),"account_id":self.account_id,"message":"Login detectado." if valid else "Faça login na janela Chrome."}
    def _group(self,url):
        url=group_url(url)
        if not self._status()["logged_in"]:raise ValueError("Faça login no Facebook.")
        self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
        return {"message":"Grupo aberto; confira se tem permissão de publicar."}
    def _find(self,selectors,avoid_articles=False):
        for s in selectors:
            try:
                loc=self.page.locator(s)
                # Não assumir que .first() é o botão certo, especialmente em grupos com comentários.
                for i in range(min(loc.count(),12)):
                    e=loc.nth(i)
                    if not e.is_visible():
                        continue
                    if avoid_articles and e.evaluate("(el) => Boolean(el.closest('[role=article]'))"):
                        continue
                    return e
            except Exception:
                continue
        return None

    def _assert_caption(self,expected,op_id):
        if not expected:
            return
        editor=self._find(EDITORS)
        if editor is None:
            raise ValueError("CAPTION_LOST_AFTER_UPLOAD: editor da legenda desapareceu.")
        actual=editor.evaluate("(el) => el.innerText || el.textContent || ''")
        if not caption_matches(expected,actual):
            raise ValueError("CAPTION_LOST_AFTER_UPLOAD: legenda divergente; cancelado antes do clique.")
        self._emit(op_id,"CAPTION_RECHECK_PASSED")
    def _publish(self,url,caption,media,operation_id=None):
        url=group_url(url)
        kind=media_kind(media)
        started=time.monotonic()
        stage="PRECHECK"
        if not self._status()["logged_in"]:
            self._emit(operation_id,"PRE_SUBMIT_FAILED",error_code="SESSION_REQUIRED",status="FAILED_BEFORE_SUBMIT")
            raise ValueError("Faça login antes de publicar.")
        clicked=False
        media_deadline=None
        try:
            stage="NAVIGATE_GROUP"
            self._emit(operation_id,stage,group_id=url.split("/groups/")[1].strip("/"),media_kind=kind,media_count=len(media))
            self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
            self.page.wait_for_timeout(1300)
            if "/checkpoint" in self.page.url or "/login" in self.page.url:
                raise ValueError("FACEBOOK_RESTRICTED: sessão ou checkpoint.")
            if group_url(self.page.url)!=url:
                raise ValueError("Facebook redirecionou para outro grupo ou domínio.")
            stage="FIND_COMPOSER"
            composer=self._find(COMPOSERS,avoid_articles=True)
            if composer is None:raise ValueError("Não encontrei campo de criação de publicação no grupo.")
            composer.click();self.page.wait_for_timeout(900)
            self._emit(operation_id,"COMPOSER_OPEN",duration_ms=int((time.monotonic()-started)*1000))
            if caption:
                editor=self._find(EDITORS)
                if editor is None:raise ValueError("Não encontrei editor da legenda.")
                editor.fill(caption)
                self._emit(operation_id,"CAPTION_FILLED")
            if media:
                stage="MEDIA_INPUT"
                kind=media_kind(media)
                # Fotografias antigas e avatares já existentes não são prévias desta operação.
                gallery_selector='[role="dialog"] img[src*="blob:"]'
                existing_src=self.page.locator(gallery_selector).evaluate_all(
                    "(els) => els.map(el => el.currentSrc || el.src).filter(Boolean)"
                )
                input_sel='[role="dialog"] input[type="file"]'
                inputs=self.page.locator(input_sel)
                accepts=inputs.evaluate_all("(els) => els.map(el => el.getAttribute('accept') || '')")
                index=pick_file_input_index(accepts,kind) if accepts else None
                if index is not None:
                    # Caminho normal: não clicar Foto/vídeo e não abrir diálogo nativo do Windows.
                    fi=inputs.nth(index)
                    if len(media)>1 and fi.get_attribute("multiple") is None:
                        raise ValueError("O input escolhido não aceita múltiplos arquivos.")
                    fi.set_input_files(media,timeout=30000)
                    observed=input_file_count(fi)
                    route="DIRECT_INPUT"
                else:
                    # Input dinâmico: capturar o FileChooser do Playwright em vez de deixar
                    # o seletor nativo aberto enquanto fazemos um segundo upload.
                    mb=self._find(MEDIA_BUTTONS)
                    if mb is None:
                        raise ValueError("Input e botão de mídia ausentes no compositor.")
                    with self.page.expect_file_chooser(timeout=12000) as chooser:
                        mb.click(timeout=4000)
                    fc=chooser.value
                    if len(media)>1 and not fc.is_multiple():
                        raise ValueError("O FileChooser não aceita múltiplos arquivos.")
                    fc.set_files(media,timeout=30000)
                    observed=fc.element.evaluate("(el) => el.files ? el.files.length : -1")
                    route="PLAYWRIGHT_FILE_CHOOSER"
                self._emit(operation_id,"UPLOAD_ROUTE_SELECTED",upload_method=route)
                self._emit(operation_id,"FILES_ASSIGNED",media_count=len(media),
                           observed_count=observed,status=("FILES_MATCHED" if observed==len(media) else "INPUT_CLEARED_OR_UNKNOWN"))
                if observed not in (len(media),0):
                    raise ValueError(f"Facebook recebeu {observed}/{len(media)} arquivos no input.")
                media_deadline=time.monotonic()+wait_budget_ms(
                    kind,len(media),sum(Path(p).stat().st_size for p in media)
                )/1000
                stage="MEDIA_PREVIEW"
                if kind=="image":
                    # Não inferir N fotos pela presença genérica de um botão Editar.
                    # Para 6 fotos, a colagem pode mostrar quatro miniaturas + selo '+2'.
                    gallery_script=r"""(before) => {
                        const old=new Set(before);
                        const dialog=[...document.querySelectorAll('[role="dialog"]')].find(el => {
                            const r=el.getBoundingClientRect();
                            return r.width>100 && r.height>100 && getComputedStyle(el).visibility!=='hidden';
                        });
                        if(!dialog) return {visible:0,overflow:null};
                        const visible=[...dialog.querySelectorAll('img[src*="blob:"]')]
                          .filter(el=>{
                            const r=el.getBoundingClientRect();
                            const src=el.currentSrc||el.src;
                            return r.width>=40 && r.height>=40 && el.complete && el.naturalWidth>0
                              && src && !old.has(src);
                          });
                        const ids=new Set(visible.map(el=>el.currentSrc||el.src));
                        const extra=[...dialog.querySelectorAll('span,div')]
                          .filter(el=>el.children.length===0 && el.getBoundingClientRect().width>0)
                          .map(el=>(el.textContent||'').trim())
                          .map(s=>s.match(/^\+(\d+)$/)||s.match(/^mais\s+(\d+)$/i))
                          .filter(Boolean).map(m=>Number(m[1]));
                        return {visible:ids.size,overflow:extra.length===1?extra[0]:null};
                    }"""
                    last_evidence={"visible":0,"overflow":None}
                    while time.monotonic()<media_deadline:
                        last_evidence=self.page.evaluate(gallery_script,existing_src)
                        if gallery_complete(len(media),last_evidence["visible"],
                                            last_evidence["overflow"],observed):
                            break
                        self.page.wait_for_timeout(400)
                    else:
                        self._emit(operation_id,"MEDIA_PREVIEW_INCOMPLETE",
                                   observed_count=last_evidence["visible"],
                                   overflow_count=last_evidence["overflow"])
                        raise ValueError(f"Prévia de {len(media)} fotos não comprovada; envio cancelado.")
                    self._emit(operation_id,"MEDIA_PREVIEW_READY",
                               observed_count=last_evidence["visible"],
                               overflow_count=last_evidence["overflow"])
                else:
                    try:
                        self.page.wait_for_function(
                            """before => {
                              const old=new Set(before);
                              const videos=[...document.querySelectorAll('[role="dialog"] video')];
                              if(videos.some(v=>v.getBoundingClientRect().width>=40
                                    && v.getBoundingClientRect().height>=40)) return true;
                              return [...document.querySelectorAll('[role="dialog"] img[src*="blob:"], [role="dialog"] img[src*="scontent"]')]
                                .some(img => {
                                  const src=img.currentSrc||img.src;
                                  return src && !old.has(src) && img.getBoundingClientRect().width>=40;
                                });
                            }""",arg=existing_src,timeout=remaining_budget_ms(media_deadline)
                        )
                    except Exception as exc:
                        raise ValueError("Prévia do vídeo ausente; não publicar.") from exc
                    self._emit(operation_id,"MEDIA_PREVIEW_READY",
                               duration_ms=int((time.monotonic()-started)*1000))
                stage="RECHECK_CAPTION"
                self._assert_caption(caption,operation_id)
            stage="FIND_PUBLISH_BUTTON"
            # Para anexos, não buscar botões de feed fora do diálogo de publicação.
            btn=self._find(POST_BUTTONS[:8] if media else POST_BUTTONS)
            if btn is None:
                dialogs=self.page.get_by_role("dialog")
                for i in range(dialogs.count()):
                    d=dialogs.nth(i)
                    if d.is_visible():
                        b=d.get_by_role("button",name=POST_NAME)
                        if b.count() and b.last.is_visible():
                            btn=b.last;break
                if btn is None and not media:
                    btn=self.page.get_by_role("button",name=POST_NAME).last
            if btn is None:
                raise ValueError("Botão Publicar não encontrado no compositor.")
            btn.wait_for(state="visible",timeout=remaining_budget_ms(media_deadline))
            if media:
                from playwright.sync_api import expect
                # Botão habilitado é indício de readiness, não prova definitiva de upload.
                expect(btn).to_be_enabled(timeout=remaining_budget_ms(media_deadline))
            # O Facebook pode re-renderizar a legenda mesmo após validar a prévia.
            self._assert_caption(caption,operation_id)
            self._emit(operation_id,"BUTTON_READY",duration_ms=int((time.monotonic()-started)*1000))
            # Marker primeiro: quedas entre journal/evento e clique permanecem conservadoras.
            if self.audit is not None and operation_id:
                self.audit.mark_submit_intent(operation_id)
            self._journal_submit_attempt(url,operation_id)
            if self.audit is not None and operation_id:
                self.audit.emit(operation_id,"SUBMIT_INTENT",durable=True,
                    account_id=self.account_id,group_id=url.split("/groups/")[1].strip("/"),
                    status="SUBMITTED_UNVERIFIED")
            clicked=True
            stage="SUBMIT_CLICK"
            self.last_submission={"operation_id":operation_id,"account_id":self.account_id,
                                  "media_kind":kind}
            btn.click(timeout=20000 if media else 15000)
            self._emit(operation_id,"SUBMIT_RETURNED",
                       duration_ms=int((time.monotonic()-started)*1000))
            # Diferente do clique, o Facebook pode manter a UI em "Postando"
            # e processar o vídeo por vários minutos. Aguardar um estado observável,
            # com limite; NUNCA reenviar, fechar modal ou atualizar a página.
            state=self._monitor_post_submit(operation_id,kind,started)
            pending=state=="PENDING_REVIEW"
            status="PENDING_REVIEW" if pending else "SUBMITTED_UNVERIFIED"
            self._emit(operation_id,status,status=status,post_ui_state=state,
                       duration_ms=int((time.monotonic()-started)*1000))
            if state=="POSTING_STILL_VISIBLE":
                message=("Facebook ainda mostra Postando. A operação é incerta; "
                         "não clique novamente. Confira o estado na mesma janela.")
            elif state=="VIDEO_PROCESSING":
                message=("Facebook indicou processamento do vídeo. "
                         "Ainda não foi comprovada reprodução no grupo.")
            else:
                message="Clique realizado. Verifique no grupo antes de tentar novamente."
            return {"status":status,"post_ui_state":state,"message":message,
                    "group_url":url}
        except Exception as e:
            code=error_code(stage,e)
            if clicked:
                if self.last_submission is None:
                    self.last_submission={"operation_id":operation_id,
                                          "account_id":self.account_id,
                                          "media_kind":kind}
                self._emit(operation_id,"SUBMITTED_UNVERIFIED",status="SUBMITTED_UNVERIFIED",error_code=code,duration_ms=int((time.monotonic()-started)*1000))
                return {"status":"SUBMITTED_UNVERIFIED",
                        "post_ui_state":"OBSERVATION_UNAVAILABLE",
                        "message":"O clique pode ter ocorrido; confira o grupo antes de outra tentativa.",
                        "group_url":url,"error_code":code}
            self._emit(operation_id,"PRE_SUBMIT_FAILED",status="FAILED_BEFORE_SUBMIT",error_code=code,duration_ms=int((time.monotonic()-started)*1000))
            raise ValueError("Falha antes de clicar Publicar: "+str(e)[:260]) from e
    def _post_state(self):
        """Somente observação local da aba; não navega, clica ou altera a publicação."""
        if not self.page or self.page.is_closed():
            return {"state":"BROWSER_UNAVAILABLE","operation_id":
                    self.last_submission["operation_id"] if self.last_submission else None}
        try:
            from app.post_state import POST_UI_JS, classify_post_ui
            flags=self.page.evaluate(POST_UI_JS)
            state=classify_post_ui(flags)
        except Exception:
            flags={}
            state="OBSERVATION_UNAVAILABLE"
        result={"state":state,"operation_id":
                self.last_submission["operation_id"] if self.last_submission else None}
        if self.last_submission:
            result["media_kind"]=self.last_submission["media_kind"]
            result["account_id"]=self.last_submission["account_id"]
        return result

    def _monitor_post_submit(self,operation_id,kind,started):
        """Monitoramento com limite. Retorno não implica publicação confirmada."""
        budget=90 if kind=="video" else 45
        end=time.monotonic()+budget
        previous=None
        while time.monotonic()<end:
            state=self._post_state()["state"]
            if state!=previous:
                self._emit(operation_id,"POST_UI_OBSERVED",post_ui_state=state,
                           duration_ms=int((time.monotonic()-started)*1000))
                previous=state
            if state in {"PENDING_REVIEW","VIDEO_PROCESSING","POST_UI_CLOSED_UNVERIFIED",
                         "FACEBOOK_WARNING","BROWSER_UNAVAILABLE"}:
                return state
            self.page.wait_for_timeout(1250)
        state=self._post_state()["state"]
        if state in {"POSTING_IN_PROGRESS","DIALOG_OPEN_UNVERIFIED"}:
            state="POSTING_STILL_VISIBLE"
        self._emit(operation_id,"POST_MONITOR_LIMIT",post_ui_state=state,
                   duration_ms=int((time.monotonic()-started)*1000))
        return state

    def _journal_submit_attempt(self,url,operation_id=None):
        # Persistir ANTES do clique: se o processo cair, não há licença para reenviar.
        self.data_dir.mkdir(parents=True,exist_ok=True)
        from datetime import datetime,timezone
        event={"at":datetime.now(timezone.utc).isoformat(),"operation_id":operation_id,"status":"SUBMIT_ATTEMPTED","account_id":self.account_id,"group_url":url}
        with (self.data_dir/"attempts.jsonl").open("a",encoding="utf-8") as f:
            f.write(json.dumps(event,ensure_ascii=False)+"\n")
            f.flush()
            os.fsync(f.fileno())

    def _close(self):
        try:
            if self.ctx:self.ctx.close()
        finally:
            self.ctx=None;self.page=None
            if self.pw:self.pw.stop();self.pw=None
    async def shutdown(self):
        await self.run("close")
        self.pool.shutdown(wait=False,cancel_futures=True)
