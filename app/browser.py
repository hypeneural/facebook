"""Playwright na mesma thread, perfil Chrome persistente; uma tentativa por operação."""
import asyncio
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.validation import group_url

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
        self.root=Path(root);self.pool=ThreadPoolExecutor(max_workers=1);self.pw=None;self.ctx=None;self.page=None
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
        if not self.ctx or not self.page or self.page.is_closed():return {"logged_in":False,"message":"Abra o Chrome."}
        try: valid=any(c["name"]=="c_user" and c["value"] for c in self.ctx.cookies("https://www.facebook.com/"))
        except Exception:valid=False
        return {"logged_in":bool(valid),"message":"Login detectado." if valid else "Faça login na janela Chrome."}
    def _group(self,url):
        url=group_url(url)
        if not self._status()["logged_in"]:raise ValueError("Faça login no Facebook.")
        self.page.goto(url,wait_until="domcontentloaded",timeout=45000)
        return {"message":"Grupo aberto; confira se tem permissão de publicar."}
    def _find(self,selectors):
        for s in selectors:
            try:
                e=self.page.locator(s).first
                e.wait_for(state="visible",timeout=1600)
                return e
            except Exception:continue
        return None
    def _publish(self,url,caption,media):
        url=group_url(url)
        if not self._status()["logged_in"]:raise ValueError("Faça login antes de publicar.")
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
            # Um timeout pode ocorrer DEPOIS do clique: nao reenvie automaticamente.
            clicked=True
            btn.click(timeout=120000 if media else 15000)
            self.page.wait_for_timeout(1900)
            pending=self.page.get_by_text(re.compile("aguardando aprovação|pending approval",re.I))
            return {"status":"PENDING_REVIEW" if pending.count() and pending.first.is_visible() else "SUBMITTED_UNVERIFIED","message":"Clique realizado. Verifique no grupo antes de tentar novamente.","group_url":url}
        except Exception as e:
            if clicked:return {"status":"SUBMITTED_UNVERIFIED","message":"O clique pode ter ocorrido; confira o grupo antes de outra tentativa.","group_url":url}
            raise ValueError("Falha antes de clicar Publicar: "+str(e)[:260]) from e
    def _close(self):
        try:
            if self.ctx:self.ctx.close()
        finally:
            self.ctx=None;self.page=None
            if self.pw:self.pw.stop();self.pw=None
    async def shutdown(self):
        await self.run("close")
        self.pool.shutdown(wait=False,cancel_futures=True)
