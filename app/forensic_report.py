"""Exportador de evidências SEM credenciais/legendas/DOM/path.

Recebe estruturas já parseadas. Tudo que não estiver na allowlist é descartado.
Pode ser versionado no GitHub; os logs brutos permanecem exclusivamente em data/.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib
import re

UUID=re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,64}$")
CODE=re.compile(r"^[A-Z][A-Z0-9_]{0,60}$")
ISO=re.compile(r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d[0-9.+:-]*$")
ALLOWED_JOB_STATES={"PLANNED","NEEDS_REVIEW","MISSED","SKIPPED","VERIFIED_EXTERNALLY"}
ALLOWED_STAGES={
"REQUEST_ACCEPTED","FILES_STAGED","GROUP_DESTINATION_VERIFIED","COMPOSER_OPEN",
"CAPTION_FILLED","MEDIA_PREVIEW_READY","CAPTION_RECHECK_PASSED","BUTTON_READY",
"PRE_SUBMIT_DESTINATION_RECHECK","SUBMIT_INTENT","SUBMIT_RETURNED",
"POST_UI_OBSERVED","API_RESPONSE","PRE_SUBMIT_FAILED","SUBMITTED_UNVERIFIED",
"PENDING_REVIEW","UPLOAD_REJECTED","HISTORY_WRITE_FAILED","UPLOAD_ROUTE_SELECTED",
"POSTING_IN_PROGRESS","POSTING_STILL_VISIBLE","VIDEO_PROCESSING","TIMEOUT",
"GROUP_OPEN_REQUESTED","GROUP_COMPOSER_READY","GROUP_COMPOSER_NOT_FOUND",
"GROUP_DESTINATION_MISMATCH","FAILED_BEFORE_SUBMIT",
}
ALLOWED_EVENT={"MISSED","CLAIMED_UNCERTAIN","DISPATCH_RESULT",
               "MANUAL_RESOLUTION","PREFLIGHT_FAILED"}
NUMERIC={"media_count","bytes_total","duration_ms","observed_count","overflow_count"}
STATE_KEYS={"status","post_ui_state","media_kind","upload_method"}
SAFE_STATE=re.compile(r"^[A-Z0-9_]{2,50}$")

def digest_id(value):
    """Desidentificador determinístico para conta, grupo e artefato; não reversível."""
    if value is None:return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]

def safe_uuid(value):
    return str(value)[:64] if UUID.fullmatch(str(value)) else None

KNOWN_CODES={
 "NO_AUTORETRY","MISSED_WINDOW","SERVER_NOT_READY","STALE_SERVER","ACCOUNT_NOT_READY",
 "PREVIOUS_POST_NOT_CLEARED","PREFLIGHT_UNKNOWN","CONFIG_OR_MEDIA_CHANGED",
 "CONFIG_CHANGED","CAPTION_INVALID","MEDIA_MANIFEST_INVALID",
 "MEDIA_MISSING_OR_SYMLINK","MEDIA_SIZE_INVALID","CONTENT_CHECK_FAILED",
 "SUBMITTED_UNVERIFIED","PENDING_REVIEW","FAILED_BEFORE_SUBMIT","UPLOAD_REJECTED",
 "TRANSPORT_OR_PUBLISH_UNCERTAIN","PLAN_CHANGED","UNEXPECTED_API_RESPONSE",
 "FACEBOOK_RESTRICTED","SESSION_REQUIRED","DESTINATION_MISMATCH",
 "COMPOSER_NOT_FOUND","MEDIA_INPUT_ERROR","PREVIOUS_POST_STILL_ACTIVE",
 "EDITOR_AMBIGUOUS","CAPTION_EDITOR_NOT_FOUND","CAPTION_LOST_AFTER_UPLOAD",
 "FILE_CHOOSER_ERROR","MEDIA_PREVIEW_UNVERIFIED","PUBLISH_BUTTON_ERROR",
 "HISTORY_IO_ERROR","NO_OPERATION","POST_UI_CLOSED_UNVERIFIED",
}
def safe_code(value):
    v=str(value)
    if v in KNOWN_CODES:return v
    if CODE.fullmatch(v) and v.startswith(("UNCLASSIFIED_","TIMEOUT_AT_")):return v
    if re.fullmatch(r"(?:SKIPPED|VERIFIED_EXTERNALLY)_[0-9a-f]{12}",v):return v
    return "UNCLASSIFIED"

def safe_time(value):
    v=str(value)
    return v[:35] if ISO.fullmatch(v) else None

def sanitize_operation(row):
    if not isinstance(row,dict):return None
    uid=safe_uuid(row.get("operation_id"))
    if uid is None:return None
    x={"operation_id":uid}
    job_id=row.get("job_id")
    if isinstance(job_id,str) and re.fullmatch(r"[0-9a-f]{32}",job_id):
        x["job_id"]=job_id
    run_id=safe_uuid(row.get("run_id"))
    if run_id:x["run_id"]=run_id
    for k in ("account_id","group_id"):
        if row.get(k) is not None:x[k+"_hash"]=digest_id(row[k])
    for k in ("at",):
        v=safe_time(row.get(k))
        if v:x[k]=v
    if row.get("stage") in ALLOWED_STAGES:x["stage"]=row["stage"]
    for k in NUMERIC:
        if type(row.get(k)) is int and 0<=row[k]<=2**44:
            x[k]=row[k]
    for k in STATE_KEYS:
        val=row.get(k)
        if isinstance(val,str) and SAFE_STATE.fullmatch(val):x[k]=val
    if "error_code" in row:x["error_code"]=safe_code(row["error_code"])
    if isinstance(row.get("error_class"),str) and re.fullmatch(r"[A-Za-z0-9_]{2,60}",row["error_class"]):
        x["error_class"]=row["error_class"]
    if isinstance(row.get("source_file"),str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",row["source_file"]):
        x["source_file"]=row["source_file"]
    if type(row.get("source_line")) is int and 0<row["source_line"]<100000:
        x["source_line"]=row["source_line"]
    return x

def sanitize_job(row):
    if not isinstance(row,dict):return None
    jid=row.get("id")
    if not isinstance(jid,str) or not re.fullmatch(r"[0-9a-f]{32}",jid):return None
    x={"job_id":jid,"status":row["status"] if row.get("status") in ALLOWED_JOB_STATES else "UNKNOWN"}
    for k in ("group_id","account_id","creative_id","caption_id"):
        if k in row:x[k+"_hash"]=digest_id(row[k])
    for k in ("day","slot","due_utc","checked_at"):
        value=str(row.get(k,""))
        if k=="day" and re.fullmatch(r"\d{4}-\d\d-\d\d",value):x[k]=value
        elif k=="slot" and re.fullmatch(r"\d\d:\d\d",value):x[k]=value
        elif k in ("due_utc","checked_at"):
            v=safe_time(value)
            if v:x[k]=v
    operation=safe_uuid(row.get("operation_id"))
    if operation:x["operation_id"]=operation
    return x

def sanitize_tick(row):
    if not isinstance(row,dict):return None
    if row.get("stage") not in {"TICK_START","TICK_END","TICK_RESULT","TICK_EXCEPTION","FORENSICS_EXPORT_FAILED"}:
        return None
    run_id=safe_uuid(row.get("run_id"))
    if not run_id:return None
    x={"run_id":run_id,"stage":row["stage"]}
    job_id=row.get("job_id")
    if isinstance(job_id,str) and re.fullmatch(r"[0-9a-f]{32}",job_id):
        x["job_id"]=job_id
    operation_id=safe_uuid(row.get("operation_id"))
    if operation_id:x["operation_id"]=operation_id
    state=row.get("state")
    if isinstance(state,str) and SAFE_STATE.fullmatch(state):
        x["state"]=state
    if row.get("error_code") is not None:
        x["error_code"]=safe_code(row["error_code"])
    at=safe_time(row.get("at"))
    if at:x["at"]=at
    for k in ("pid","exit_code","duration_ms"):
        v=row.get(k)
        if type(v) is int and -10000<=v<=2**40:x[k]=v
    if isinstance(row.get("error_class"),str) and re.fullmatch(r"[A-Za-z]{2,60}",row["error_class"]):
        x["error_class"]=row["error_class"]
    return x

def sanitize_server_run(row):
    if not isinstance(row,dict) or row.get("stage") not in {
        "SERVER_LOGON_START","SERVER_LOGON_END","SERVER_LOGON_FAILED"}:
        return None
    run_id=safe_uuid(row.get("run_id"))
    if not run_id:return None
    event={"run_id":run_id,"stage":row["stage"]}
    at=safe_time(row.get("at"))
    if at:event["at"]=at
    for key in ("exit_code","duration_ms"):
        value=row.get(key)
        if type(value) is int and 0<=value<=2**40:
            event[key]=value
    cls=row.get("error_class")
    if isinstance(cls,str) and re.fullmatch(r"[A-Za-z]{2,60}",cls):
        event["error_class"]=cls
    return event


def summarize(raw_jobs,raw_events,raw_ops,windows=None,raw_ticks=None,raw_server_runs=None):
    jobs=[v for r in raw_jobs if (v:=sanitize_job(r))]
    # Hash redaction of account/group; stage only from enumerated allowed values.
    ops=[v for r in raw_ops if (v:=sanitize_operation(r))]
    events=[]
    for row in raw_events:
        if not isinstance(row,dict) or row.get("event") not in ALLOWED_EVENT:continue
        jid=row.get("job_id")
        if not isinstance(jid,str) or not re.fullmatch(r"[0-9a-f]{32}",jid):continue
        at=safe_time(row.get("at"))
        events.append({"job_id":jid,"at":at,"event":row["event"],
                       "code":safe_code(row.get("code"))})
    statuses=Counter(x["status"] for x in jobs)
    result={
        "schema":"facebook.forensic.v1",
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provenance":"local_sanitized_export_not_external_facebook_proof",
        "totals":{"jobs":len(jobs),"operations":len(ops),"job_events":len(events),
                  "job_statuses":dict(sorted(statuses.items()))},
        "jobs":jobs[-500:],"job_events":events[-2500:],"operations":ops[-2500:],
        "ticks":[v for r in (raw_ticks or []) if (v:=sanitize_tick(r))][-3000:],
        "server_runs":[v for r in (raw_server_runs or []) if (v:=sanitize_server_run(r))][-1000:]
    }
    # Windows diagnostics contains only allowlisted aggregated metadata.
    if isinstance(windows,dict) and windows.get("schema")=="facebook.win11.v1":
        task=windows.get("task") if isinstance(windows.get("task"),dict) else {}
        result["windows"]={
            "schema":"facebook.win11.v1",
            "os_family":"Windows",
            "task_exists":task.get("exists") is True,
            "task_state":task.get("state") if task.get("state") in
                {"Ready","Running","Disabled","Queued","Unknown"} else "Unknown",
            "last_result_code":str(task.get("last_result_code"))[:16] if re.fullmatch(r"-?\d{1,15}",str(task.get("last_result_code"))) else None,
            "last_run_utc":safe_time(task.get("last_run_utc")),
            "next_run_utc":safe_time(task.get("next_run_utc")),
            "missed_runs":task.get("missed_runs") if type(task.get("missed_runs")) is int and 0<=task["missed_runs"]<=100000000 else None,
            "multiple_instances":task.get("multiple_instances") if task.get("multiple_instances") in {"IgnoreNew","Queue","Parallel","StopExisting"} else "Unknown",
            "logon_type":task.get("logon_type") if task.get("logon_type") in {"Interactive","Password","S4U","Group","ServiceAccount","InteractiveOrPassword","None"} else "Unknown",
            "execution_limit_minutes":task.get("execution_limit_minutes") if type(task.get("execution_limit_minutes")) is int and 0<=task["execution_limit_minutes"]<=1000000 else None,
            "event_scan_count":windows.get("event_scan_count") if type(windows.get("event_scan_count")) is int and 0<=windows["event_scan_count"]<=1000000 else None,
            "event_scan_truncated":windows.get("event_scan_truncated") is True,
            "recent_scheduler_event_ids":[x for x in windows.get("recent_event_ids",[])[:100]
                if type(x) is int and 0<=x<=10000],
            "recent_events":[{"event_id":int(x["event_id"]),"at_utc":safe_time(x["at_utc"])}
                for x in windows.get("recent_events",[])[:100]
                if isinstance(x,dict) and type(x.get("event_id")) is int
                and 0<=x["event_id"]<=10000 and safe_time(x.get("at_utc"))],
            "collection_errors":[e for e in windows.get("errors",[])[:20]
                if isinstance(e,str) and re.fullmatch(r"(?:TASK_QUERY|EVENT_LOG)_[A-Za-z]{2,60}",e)],
        }
    return result
