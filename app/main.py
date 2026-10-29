"""Painel local, sem serviços Cloud ou credenciais do Facebook."""
import asyncio
import json
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
from fastapi import FastAPI,File,Form,UploadFile,Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel
from app.browser import Browser
from app.validation import validate,group_url

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
browser=None
publish_lock=asyncio.Lock()

@asynccontextmanager
async def lifespan(app):
    global browser
    DATA.mkdir(parents=True,exist_ok=True)
    browser=Browser(DATA/"chrome-profile")
    yield
    await browser.shutdown()
app=FastAPI(title="Facebook Grupos MVP",lifespan=lifespan)
@app.middleware("http")
async def local_only(request:Request,call_next):
    host=(request.headers.get("host") or "").split(":")[0].lower()
    if host not in {"localhost","127.0.0.1"}:return JSONResponse({"detail":"Acesso externo bloqueado."},status_code=403)
    if request.method not in {"GET","HEAD","OPTIONS"}:
        origin=request.headers.get("origin","")
        if origin and origin not in {"http://localhost:8108","http://127.0.0.1:8108"}:return JSONResponse({"detail":"Origem bloqueada."},status_code=403)
        if request.headers.get("sec-fetch-site")=="cross-site":return JSONResponse({"detail":"Origem cruzada bloqueada."},status_code=403)
    return await call_next(request)
@app.get("/")
def home():return FileResponse(ROOT/"app"/"static"/"index.html")
@app.get("/health")
def health():return {"ok":True,"real_facebook_publish_verified":False}
@app.post("/api/browser/open")
async def open_browser():
    try:return await browser.run("open")
    except Exception as e:raise HTTPException(409,str(e)[:260])
@app.get("/api/session")
async def session():return await browser.run("status")
class GroupBody(BaseModel):group_url:str
@app.post("/api/group/open")
async def group(body:GroupBody):
    try:return await browser.run("group",group_url(body.group_url))
    except Exception as e:raise HTTPException(409,str(e)[:260])
@app.get("/api/history")
def history():
    path=DATA/"history.jsonl"
    if not path.exists():return []
    return [json.loads(s) for s in reversed(path.read_text(encoding="utf8").splitlines()[-20:]) if s.strip()]
@app.post("/api/publish")
async def publish(group_url:str=Form(...),caption:str=Form(""),media:list[UploadFile]|None=File(None)):
    files=media or []
    try:url=validate(group_url,caption,[f.filename or "" for f in files])
    except ValueError as e:raise HTTPException(422,str(e))
    if publish_lock.locked():raise HTTPException(409,"Já existe uma publicação em andamento.")
    job=DATA/"uploads"/str(uuid.uuid4())
    try:
        async with publish_lock:
            job.mkdir(parents=True,exist_ok=False)
            names=[];size=0
            for i,f in enumerate(files):
                target=job/(f"{i:02d}"+Path(f.filename or "").suffix.lower())
                with target.open("wb") as out:
                    while part:=await f.read(1024*1024):
                        size+=len(part)
                        if size>300*1024*1024:raise HTTPException(413,"Limite total 300 MB.")
                        out.write(part)
                if not target.stat().st_size:raise HTTPException(422,"Arquivo vazio.")
                names.append(str(target.resolve()))
            try:result=await browser.run("publish",url,caption.strip(),names)
            except Exception as e:result={"status":"FAILED_BEFORE_SUBMIT","message":str(e)[:300],"group_url":url}
            result["at"]=datetime.now(timezone.utc).isoformat()
            with (DATA/"history.jsonl").open("a",encoding="utf8") as h:h.write(json.dumps(result,ensure_ascii=False)+"\n")
            return result
    finally:
        for f in files:await f.close()
        shutil.rmtree(job,ignore_errors=True)
