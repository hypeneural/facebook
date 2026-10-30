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
from app.media_policy import media_kind
from app.telemetry import AuditTrail, group_id, error_code

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
browser=None
publish_lock=asyncio.Lock()

@asynccontextmanager
async def lifespan(app):
    global browser
    DATA.mkdir(parents=True,exist_ok=True)
    browser=Browser(DATA/"chrome-profile")
    browser.audit=AuditTrail(DATA)
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

class ProfileCreate(BaseModel):
    name:str

class ProfileSelect(BaseModel):
    account_id:str

@app.get("/api/accounts")
async def accounts():return await browser.run("accounts")

@app.post("/api/accounts")
async def add_account(body:ProfileCreate):
    if publish_lock.locked():raise HTTPException(409,"Aguarde a publicação em andamento.")
    try:return await browser.run("add_account",body.name)
    except ValueError as e:raise HTTPException(422,str(e))

@app.post("/api/accounts/select")
async def select_account(body:ProfileSelect):
    if publish_lock.locked():raise HTTPException(409,"Não troque conta durante um envio.")
    try:return await browser.run("select_account",body.account_id)
    except ValueError as e:raise HTTPException(422,str(e))

class GroupCreate(BaseModel):
    name:str
    group_url:str

def _read_groups():
    p=DATA/"groups.json"
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else []

@app.get("/api/groups/saved")
def saved_groups():return _read_groups()

@app.post("/api/groups/saved")
def add_group(body:GroupCreate):
    if publish_lock.locked():raise HTTPException(409,"Não altere grupo durante uma publicação.")
    name=body.name.strip()
    if not (1<=len(name)<=90):raise HTTPException(422,"Nome do grupo inválido.")
    try:url=group_url(body.group_url)
    except ValueError as e:raise HTTPException(422,str(e))
    groups=_read_groups()
    if not any(g["url"]==url for g in groups):
        if len(groups)>=100:raise HTTPException(422,"Limite de grupos salvos.")
        groups.append({"name":name,"url":url})
        DATA.mkdir(parents=True,exist_ok=True)
        tmp=DATA/"groups.json.tmp"
        tmp.write_text(json.dumps(groups,ensure_ascii=False,indent=2),encoding="utf8")
        tmp.replace(DATA/"groups.json")
    return groups
class GroupBody(BaseModel):group_url:str
@app.post("/api/group/open")
async def group(body:GroupBody):
    try:return await browser.run("group",group_url(body.group_url))
    except Exception as e:raise HTTPException(409,str(e)[:260])
@app.get("/api/operations")
def operations():
    # Apenas metadados de estágios, sem legendas, nomes de arquivos ou cookies.
    return browser.audit.recent(limit=30)

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
            operation_id=job.name
            audit=browser.audit
            audit.emit(operation_id,"REQUEST_ACCEPTED",durable=True,account_id=browser.account_id,group_id=group_id(url),media_kind=media_kind([f.filename or "" for f in files]),media_count=len(files))
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
            audit.emit(operation_id,"FILES_STAGED",account_id=browser.account_id,group_id=group_id(url),media_kind=media_kind(names),media_count=len(names),bytes_total=size)
            try:
                result=await browser.run("publish",url,caption.strip(),names,operation_id)
            except Exception as e:
                uncertain=audit.submitted_intent_exists(operation_id)
                result={"status":"SUBMITTED_UNVERIFIED" if uncertain else "FAILED_BEFORE_SUBMIT",
                        "message":"Resultado incerto. Verifique no grupo." if uncertain else str(e)[:300],
                        "group_url":url,"error_code":error_code("BROWSER_RUN",e)}
                audit.emit(operation_id,"SUBMITTED_UNVERIFIED" if uncertain else "PRE_SUBMIT_FAILED",account_id=browser.account_id,status=result["status"],error_code=result["error_code"])
            result["operation_id"]=operation_id
            result["account_id"]=(await browser.run("accounts"))["active"]
            result["at"]=datetime.now(timezone.utc).isoformat()
            with (DATA/"history.jsonl").open("a",encoding="utf8") as h:
                h.write(json.dumps(result,ensure_ascii=False)+"\n")
            audit.emit(operation_id,"API_RESPONSE",account_id=result["account_id"],status=result["status"])
            return result
    finally:
        for f in files:await f.close()
        shutil.rmtree(job,ignore_errors=True)
