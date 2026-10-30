"""Auditoria local, estruturada e sem conteúdo de clientes.
NUNCA registra legenda, fotos, paths, tokens, cookies, URLs privadas ou DOM.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading

TERMINAL={"PRE_SUBMIT_FAILED","SUBMITTED_UNVERIFIED","PENDING_REVIEW","VERIFIED_EXTERNALLY","UPLOAD_REJECTED"}
SENSITIVE_KEYS={"caption","content","text","filename","filepath","path","cookie","token","password","url","dom","html","secret","trace"}
FIELDS={"job_id","operation_id","stage","account_id","group_id","media_kind","media_count","bytes_total","duration_ms","error_code","status","upload_method","observed_count","overflow_count","post_ui_state","error_class","source_file","source_line"}


def exception_location(error):
    """Somente classe, basename de módulo e linha — nunca traceback, paths ou argumentos."""
    import re
    info={"error_class":type(error).__name__[:60]}
    tb=error.__traceback__
    if tb is None:return info
    while tb.tb_next is not None:tb=tb.tb_next
    filename=Path(tb.tb_frame.f_code.co_filename).name
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",filename):
        info["source_file"]=filename
    info["source_line"]=int(tb.tb_lineno)
    return info


def error_code(stage, error):
    # Stable categories for the AI agent. No exception text stored on disk.
    s=str(error).lower()
    if "checkpoint" in s or "account locked" in s or "restri" in s:
        return "FACEBOOK_RESTRICTED"
    if "login" in s or "sessão" in s:
        return "SESSION_REQUIRED"
    if "redirecion" in s or "outro grupo" in s:
        return "DESTINATION_MISMATCH"
    if "composer" in s or "campo de criação" in s:
        return "COMPOSER_NOT_FOUND"
    if "input de mídia" in s or "arquivo" in s:
        return "MEDIA_INPUT_ERROR"
    if "previous_post_still_active" in s:
        return "PREVIOUS_POST_STILL_ACTIVE"
    if "editor_ambiguous" in s:
        return "EDITOR_AMBIGUOUS"
    if "caption_editor_not_found" in s:
        return "CAPTION_EDITOR_NOT_FOUND"
    if "caption_lost_after_upload" in s or "legenda divergente" in s:
        return "CAPTION_LOST_AFTER_UPLOAD"
    if "filechooser" in s:
        return "FILE_CHOOSER_ERROR"
    if "prévia" in s or "preview" in s or "miniatura" in s:
        return "MEDIA_PREVIEW_UNVERIFIED"
    if "publicar" in s or "botão" in s:
        return "PUBLISH_BUTTON_ERROR"
    if "timeout" in s:
        return "TIMEOUT_AT_"+str(stage).upper().replace("-","_")[:30]
    return "UNCLASSIFIED_"+str(stage).upper().replace("-","_")[:30]


def group_id(url):
    # ID público de destino, nunca URL com parâmetros.
    import re
    m=re.search(r"/groups/([A-Za-z0-9_.-]{2,150})(?:/|$)",url or "")
    return m.group(1) if m else None


class AuditTrail:
    def __init__(self, data_dir):
        self.path=Path(data_dir)/"operations.jsonl"
        self.lock=threading.Lock()

    def emit(self, operation_id, stage, *, durable=False, **fields):
        event={
            "at":datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "operation_id":str(operation_id)[:64],
            "stage":str(stage)[:48],
        }
        for k,v in fields.items():
            if k in SENSITIVE_KEYS:
                raise ValueError("Campo sensível proibido na auditoria: "+k)
            if k in FIELDS and v is not None:
                if k in {"media_count","bytes_total","duration_ms","observed_count","overflow_count","source_line"}:
                    event[k]=int(v)
                else:
                    if k in {"error_class","source_file"}:
                        import re
                        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",str(v)):
                            continue
                    event[k]=str(v)[:90]
        self.path.parent.mkdir(parents=True,exist_ok=True)
        line=(json.dumps(event,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
        # Single os.write(O_APPEND) prevents interleaving between API and Playwright thread.
        with self.lock:
            fd=os.open(self.path,os.O_CREAT|os.O_APPEND|os.O_WRONLY,0o600)
            try:
                n=os.write(fd,line)
                if n!=len(line):
                    raise OSError("Auditoria gravou evento incompleto")
                if durable:
                    os.fsync(fd)
            finally:
                os.close(fd)
        return event

    def mark_submit_intent(self,operation_id):
        # O(1) recovery marker survives a crash and does not contain media or secrets.
        import uuid
        try:
            operation_id=str(uuid.UUID(str(operation_id)))
        except (ValueError,TypeError,AttributeError):
            raise ValueError("UUID de operação inválido") from None
        directory=self.path.parent/"submit-intents"
        directory.mkdir(parents=True,exist_ok=True)
        target=directory/operation_id
        fd=os.open(target,os.O_CREAT|os.O_WRONLY,0o600)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def recent(self,limit=30):
        if not self.path.exists():
            return []
        # Tail bounded to 1 MiB: the dashboard must not rescan years of JSONL.
        with self.lock:
            with self.path.open("rb") as f:
                f.seek(0,os.SEEK_END)
                pos=f.tell()
                chunks=[]
                size=0
                while pos>0 and size<1024*1024:
                    step=min(pos,8192,1024*1024-size)
                    pos-=step
                    f.seek(pos)
                    chunks.append(f.read(step))
                    size+=step
        lines=b"".join(reversed(chunks)).decode("utf8",errors="replace").splitlines()
        if pos>0 and lines:
            lines=lines[1:]  # first line may start in the middle of a JSON object
        grouped={}
        for line in lines:
            try:
                event=json.loads(line)
                oid=event.get("operation_id")
                if not oid:
                    continue
                info=grouped.setdefault(oid,{"operation_id":oid,"events":[]})
                info["events"].append(event)
                info["stage"]=event["stage"]
                info["at"]=event.get("at")
                for key in ("account_id","group_id","media_kind","media_count","bytes_total","error_code","status","upload_method","observed_count","overflow_count","post_ui_state"):
                    if key in event:
                        info[key]=event[key]
            except (ValueError,TypeError,KeyError):
                continue
        items=list(reversed(list(grouped.values())[-min(100,max(1,int(limit))):]))
        # A queda pode ocorrer após gravar o marcador mas antes do JSONL SUBMIT_INTENT.
        for item in items:
            if self.submitted_marker_exists(item["operation_id"]):
                item["submit_intent_durable"]=True
                if "API_RESPONSE" not in {event.get("stage") for event in item["events"]}:
                    item["status"]="SUBMITTED_UNVERIFIED"
        return items

    def submitted_marker_exists(self,operation_id):
        return (self.path.parent/"submit-intents"/str(operation_id)).is_file()

    def submitted_intent_exists(self,operation_id):
        if self.submitted_marker_exists(operation_id):
            return True
        records=self.recent(limit=100)
        return any(r["operation_id"]==operation_id and
                   any(e["stage"]=="SUBMIT_INTENT" for e in r["events"])
                   for r in records)


def next_action(item):
    stages={x.get("stage") for x in item.get("events",[])}
    code=item.get("error_code")
    if "SUBMIT_INTENT" in stages or item.get("submit_intent_durable"):
        return "VERIFICAR_NO_GRUPO_SEM_REENVIAR"
    if code=="PREVIOUS_POST_STILL_ACTIVE":
        return "AGUARDAR_E_CONFERIR_POST_ANTERIOR"
    if code=="SESSION_REQUIRED":
        return "ENTRAR_NO_FACEBOOK"
    if code in {"MEDIA_INPUT_ERROR","MEDIA_PREVIEW_UNVERIFIED"}:
        return "INSPECIONAR_MIDIA_SEM_PUBLICAR"
    if code in {"FACEBOOK_RESTRICTED","DESTINATION_MISMATCH"}:
        return "PARAR_E_VERIFICAR_ACESSO"
    if "PRE_SUBMIT_FAILED" in stages or "UPLOAD_REJECTED" in stages:
        return "CORRIGIR_ERRO_ANTES_DE_NOVA_AUTORIZACAO"
    return "ACOMPANHAR_ETAPAS"
