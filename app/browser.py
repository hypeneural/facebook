"""Playwright na mesma thread, perfil Chrome persistente; uma tentativa por operação."""
import asyncio
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.validation import group_url

COMPOSERS=['[role="button"][aria-label*="Escreva algo"]','[role="button"][aria-label*="Criar publicação"]','[role="button"][aria-label*="Write something"]','div[role="button"]:has-text("Escreva algo")','div[role="button"]:has-text("Write something")','div[role="button"]:has-text("O que você está pensando")']
EDITORS=['[role="dialog"] [contenteditable="true"][role="textbox"]','[role="dialog"] [data-lexical-editor="true"]','[role="dialog"] [contenteditable="true"]']
POST_NAME=re.compile(r"^(Publicar|Post|Publish|Compartilhar|Share|Compartilhar agora)$",re.I)
class Browser:
    def __init__(self,root):
        self.root=Path(root);self.pool=ThreadPoolExecutor(max_workers=1);self.pw=None;self.ctx=None;self.page=None
    async def run(self,name,*args):
        loop=asyncio.get_running_loop()
        return await loop.run_in_executor(self.pool,lambda:getattr(self,"_"+name)(*args))
    def _open(self):
        if self.ctx and self.page and not self.page.is_closed():
            self.page.bring_to_front();return {"message":"Chrome já aberto."}
        from playwright.sync_api import sync_playwright
        self.root.mkdir(parents=True,exist_ok=True)
        self.pw=sync_playwright().start()
        try:
            try: self.ctx=self.pw.chromium.launch_persistent_context(str(self.root),channel="chrome",headless=False,viewport={"width":1360,"height":900})
            except Exception: self.ctx=self.pw.chromium.launch_persistent_context(str(self.root),headless=False,viewport={"width":1360,"height":900})
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
                fi=self.page.locator('input[type="file"]').first
                if not fi.count():
                    for selector in ['text=Foto/vídeo','text=Photo/video']:
                        try:
                            b=self.page.locator(selector).first
                            if b.is_visible():b.click(timeout=3000);break
                        except Exception:pass
                fi=self.page.locator('input[type="file"]').first
                fi.wait_for(state="attached",timeout=12000)
                fi.set_input_files(media,timeout=20000)
                self.page.wait_for_timeout(1500)
            dialog=self.page.get_by_role("dialog").last
            scope=dialog if dialog.count() and dialog.is_visible() else self.page
            btn=scope.get_by_role("button",name=POST_NAME).last
            btn.wait_for(state="visible",timeout=12000)
            btn.click(timeout=120000 if media else 15000)
            clicked=True
            self.page.wait_for_timeout(1900)
            pending=self.page.get_by_text(re.compile("aguardando aprovação|pending approval",re.I))
            return {"status":"PENDING_REVIEW" if pending.count() and pending.first.is_visible() else "SUBMITTED_UNVERIFIED","message":"Clique realizado. Verifique no grupo antes de tentar novamente.","group_url":url}
        except Exception as e:
            if clicked:return {"status":"SUBMITTED_UNVERIFIED","message":"Clique feito; confirmação indisponível.","group_url":url}
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
