"""One-shot Windows Task Scheduler tick; safe default is PREVIEW, never publish.

Use --execute only after explicit local campaign enablement/homologation.
No browser control, private APIs, proxies, stealth, CAPTCHA bypass or retries.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import http.client
import json
import mimetypes
import os
import uuid
from pathlib import Path
import re
import secrets
import subprocess
import sys
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.daily_queue import DailyQueue,TIMEZONE,validate_config,manifest_digest
from app.validation import group_url
from app.media_policy import media_kind

def fetch_state(path,timeout=4):
    with urlopen("http://127.0.0.1:8108"+path,timeout=timeout) as r:
        return json.load(r)

def checkout_revision():
    result=subprocess.run(["git","rev-parse","--short=12","HEAD"],cwd=ROOT,
                          capture_output=True,text=True,timeout=3,check=True)
    return result.stdout.strip()

def preflight(account_id):
    health=fetch_state("/health")
    if not health.get("ok") or health.get("busy"):
        raise RuntimeError("SERVER_NOT_READY")
    if health.get("build_revision")!=checkout_revision():
        raise RuntimeError("STALE_SERVER")
    accounts=fetch_state("/api/accounts")
    session=fetch_state("/api/session")
    if accounts.get("active")!=account_id or not session.get("logged_in"):
        raise RuntimeError("ACCOUNT_NOT_READY")
    state=fetch_state("/api/post-state").get("state")
    if state not in ("NO_OPERATION","POST_UI_CLOSED_UNVERIFIED"):
        raise RuntimeError("PREVIOUS_POST_NOT_CLEARED")
    return True

def select_content(job,cfg):
    creative=next((x for x in cfg["creatives"] if x["id"]==job["creative_id"]),None)
    caption=next((x for x in cfg["captions"] if x["id"]==job["caption_id"]),None)
    if creative is None or caption is None:
        raise ValueError("CONFIG_CHANGED")
    if manifest_digest(job["group_id"],creative,caption)!=job["manifest_sha256"]:
        raise ValueError("CONFIG_OR_MEDIA_CHANGED")
    if not isinstance(caption.get("text"),str) or len(caption["text"])>5000:
        raise ValueError("CAPTION_INVALID")
    filenames=creative.get("files")
    if not isinstance(filenames,list) or not 1<=len(filenames)<=10:
        raise ValueError("MEDIA_MANIFEST_INVALID")
    media_kind(filenames)
    paths=[Path(f) for f in filenames]
    size=0
    for p in paths:
        if not p.is_file() or p.is_symlink():
            raise ValueError("MEDIA_MISSING_OR_SYMLINK")
        size+=p.stat().st_size
    if size<=0 or size>300*1024*1024:
        raise ValueError("MEDIA_SIZE_INVALID")
    url=group_url("https://www.facebook.com/groups/"+job["group_id"]+"/")
    return url,caption["text"],paths

def send_multipart(url,caption,files,*,job_id=None):
    """Streaming multipart; >300 MB never buffered in RAM or emitted into stdout."""
    boundary="FBApproved_"+secrets.token_hex(14)
    marker=boundary.encode("ascii")
    segments=[]
    def text_part(name,value):
        head=b"--"+marker+b"\r\n"+f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii")
        segments.append((head,value.encode("utf-8")+b"\r\n",None))
    text_part("group_url",url)
    text_part("caption",caption)
    if job_id is not None:
        if not re.fullmatch(r"[0-9a-f]{32}",job_id):
            raise ValueError("INVALID_JOB_ID")
        text_part("job_id",job_id)
    run_id=os.environ.get("EVYD_FORENSIC_RUN_ID")
    if run_id:
        try:
            run_id=str(uuid.UUID(run_id))
        except (ValueError,TypeError,AttributeError):
            raise ValueError("INVALID_RUN_ID") from None
        text_part("run_id",run_id)
    for i,path in enumerate(files):
        safe=re.sub(r'[^a-zA-Z0-9._-]','_',path.name)[:100]
        media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        header=(b"--"+marker+b"\r\n"+f'Content-Disposition: form-data; name="media"; filename="{safe}"\r\n'.encode("ascii")+
                f"Content-Type: {media_type}\r\n\r\n".encode("ascii"))
        segments.append((header,b"\r\n",path))
    last=b"--"+marker+b"--\r\n"
    length=len(last)+sum(len(h)+len(f)+ (p.stat().st_size if p else 0) for h,f,p in segments)
    conn=http.client.HTTPConnection("127.0.0.1",8108,timeout=900)
    try:
        conn.putrequest("POST","/api/publish")
        conn.putheader("Content-Type",f"multipart/form-data; boundary={boundary}")
        conn.putheader("Content-Length",str(length))
        conn.endheaders()
        for head,foot,path in segments:
            conn.send(head)
            if path:
                with path.open("rb") as stream:
                    while data:=stream.read(1024*1024):
                        conn.send(data)
            conn.send(foot)
        conn.send(last)
        res=conn.getresponse()
        data=res.read(64*1024)
        if res.status!=200:
            raise RuntimeError("PUBLISH_API_REJECTED")
        return json.loads(data)
    finally:
        conn.close()

def tick(cfg,store,now=None,execute=False,transport=send_multipart,state_fetch=preflight):
    validate_config(cfg)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today=now.astimezone(TIMEZONE).date()
    store.plan(cfg,today)
    if not execute:
        return {"state":"PREVIEW_ONLY","jobs":len(store.summary()),"execute":False}
    if not cfg["enabled"] or cfg.get("allow_unattended") is not True:
        return {"state":"DISABLED","execute":False}
    # Expirar primeiro: nunca fazer preflight de uma ocorrência antiga.
    store.expire_missed(now)
    if any(x["status"]=="NEEDS_REVIEW" for x in store.summary()):
        return {"state":"PAUSED_FOR_REVIEW"}
    due=[x for x in store.summary()
         if x["status"]=="PLANNED" and x["due_utc"]<=now.isoformat()]
    if not due:
        return {"state":"NO_DUE_WORK"}
    candidate=due[0]
    try:
        url,caption,paths=select_content(candidate,cfg)
    except (ValueError,OSError) as exc:
        known={"CONFIG_OR_MEDIA_CHANGED","CONFIG_CHANGED","CAPTION_INVALID",
               "MEDIA_MANIFEST_INVALID","MEDIA_MISSING_OR_SYMLINK","MEDIA_SIZE_INVALID"}
        code=str(exc)
        safe=code if code in known else "CONTENT_CHECK_FAILED"
        store.note_preflight(candidate["id"],safe)
        return {"state":"BLOCKED_CONTENT","job_id":candidate["id"],"error_code":safe}
    # Antes do claim, confirmar servidor, navegador e perfil; nenhuma troca automática.
    try:
        state_fetch(candidate["account_id"])
    except Exception as exc:
        code=str(exc)
        store.note_preflight(candidate["id"],code)
        return {"state":"WAITING_PREFLIGHT","job_id":candidate["id"],
                "error_code":code if code in {"SERVER_NOT_READY","STALE_SERVER",
                    "ACCOUNT_NOT_READY","PREVIOUS_POST_NOT_CLEARED"} else "PREFLIGHT_UNKNOWN"}
    job=store.claim_one(now)
    if job is None:
        return {"state":"PAUSED_OR_MISSED"}
    if job["id"]!=candidate["id"]:
        store.annotate(job["id"],code="PLAN_CHANGED")
        return {"state":"PAUSED_FOR_REVIEW","job_id":job["id"]}
    try:
        response=(transport(url,caption,paths,job_id=job["id"])
                  if transport is send_multipart else transport(url,caption,paths))
        status=response.get("status","SUBMITTED_UNVERIFIED")
        code=status if status in ("SUBMITTED_UNVERIFIED","PENDING_REVIEW","FAILED_BEFORE_SUBMIT") else "UNEXPECTED_API_RESPONSE"
        store.annotate(job["id"],operation_id=response.get("operation_id"),code=code)
        return {"state":"NEEDS_REVIEW","job_id":job["id"],
                "operation_id":response.get("operation_id"),"outcome":code}
    except Exception:
        # Uma chamada pode ter sido enviada. Não repetir em nenhum caso.
        store.annotate(job["id"],code="TRANSPORT_OR_PUBLISH_UNCERTAIN")
        return {"state":"NEEDS_REVIEW","job_id":job["id"],
                "outcome":"TRANSPORT_OR_PUBLISH_UNCERTAIN"}

def audit_tick_result(result):
    """Link Windows tick to a job even when HTTP did not return an operation id.

    Safe, finite structured metadata only. Never export raw exception messages,
    captions, media paths or network payloads.
    """
    run_id=os.environ.get("EVYD_FORENSIC_RUN_ID")
    try:
        run_id=str(uuid.UUID(run_id)) if run_id else None
    except (ValueError,TypeError,AttributeError):
        run_id=None
    if run_id is None or not isinstance(result,dict):
        return
    state=result.get("state")
    if not isinstance(state,str) or not re.fullmatch(r"[A-Z_]{2,50}",state):
        state="UNCLASSIFIED"
    event={"at":datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
           "run_id":run_id,"stage":"TICK_RESULT","state":state}
    jid=result.get("job_id")
    if isinstance(jid,str) and re.fullmatch(r"[0-9a-f]{32}",jid):
        event["job_id"]=jid
    op=result.get("operation_id")
    if op:
        try:
            event["operation_id"]=str(uuid.UUID(str(op)))
        except (ValueError,TypeError,AttributeError):
            pass
    code=result.get("error_code",result.get("outcome"))
    if isinstance(code,str) and re.fullmatch(r"[A-Z][A-Z0-9_]{1,60}",code):
        event["error_code"]=code
    path=ROOT/"data"/"diagnostics"/"ticks.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    line=(json.dumps(event,separators=(",",":"))+"\n").encode("utf-8")
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
    try:
        if os.write(fd,line)!=len(line):
            raise OSError("FORENSIC_TICK_SHORT_WRITE")
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=ROOT/"data"/"daily.json")
    parser.add_argument("--db",type=Path,default=ROOT/"data"/"daily-queue.sqlite")
    parser.add_argument("--execute",action="store_true",
                        help="Exige enabled=true e allow_unattended=true no arquivo local")
    parser.add_argument("--resolve-id",help="ID já aguardando conferência externa")
    parser.add_argument("--resolve-status",choices=["VERIFIED_EXTERNALLY","SKIPPED"])
    parser.add_argument("--reason",help="Justificativa da revisão humana")
    args=parser.parse_args()
    if not args.config.is_file():
        print(json.dumps({"state":"CONFIG_MISSING","template":"config/daily.example.json"}))
        return 2
    cfg=json.loads(args.config.read_text(encoding="utf-8"))
    q=DailyQueue(args.db)
    try:
        if args.resolve_id:
            if not args.resolve_status or not args.reason:
                parser.error("Informe --resolve-status e --reason.")
            q.resolve(args.resolve_id,args.resolve_status,args.reason)
            print(json.dumps({"state":"MANUALLY_RESOLVED","job_id":args.resolve_id,
                              "outcome":args.resolve_status},ensure_ascii=False))
            return 0
        result=tick(cfg,q,execute=args.execute)
        audit_tick_result(result)
        print(json.dumps(result,ensure_ascii=False))
        return 3 if result["state"] in {"NEEDS_REVIEW","PAUSED_FOR_REVIEW",
                                         "WAITING_PREFLIGHT","BLOCKED_CONTENT",
                                         "PAUSED_OR_MISSED"} else 0
    finally:q.close()

if __name__=="__main__":
    raise SystemExit(main())
