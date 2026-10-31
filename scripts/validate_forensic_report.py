"""Valida e bloqueia conteúdo inesperado antes de qualquer commit no GitHub.

Somente snapshots gerados pela ferramenta de exportação são aceitáveis.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

TOP={"schema","generated_at","provenance","totals","jobs","job_events","operations",
     "windows","ticks","server_runs","plan","build_revision","runtime","collection_errors"}
FIELDS={
 "jobs":{"job_id","status","account_id_hash","group_id_hash","creative_id_hash",
         "caption_id_hash","day","slot","due_utc","checked_at","operation_id"},
 "job_events":{"job_id","at","event","code"},
 "operations":{"operation_id","job_id","run_id","account_id_hash","group_id_hash",
               "at","stage","media_count","bytes_total","duration_ms",
               "observed_count","overflow_count","status","post_ui_state",
               "media_kind","upload_method","error_code","error_class",
               "source_file","source_line"},
 "ticks":{"run_id","stage","job_id","operation_id","state","error_code","at","pid","exit_code","duration_ms","error_class"},
 "server_runs":{"run_id","stage","at","duration_ms","exit_code","error_class"},
}
WINDOWS={"schema","os_family","task_exists","task_state","last_result_code",
         "last_run_utc","next_run_utc","missed_runs","multiple_instances",
         "logon_type","execution_limit_minutes","event_scan_truncated",
         "event_scan_count","event_log_status","server_logon_task_exists","server_logon_task_state",
         "forensic_sync_task_exists","forensic_sync_task_state",
         "recent_scheduler_event_ids","recent_events","collection_errors"}
ROW_LIMITS={"jobs":500,"job_events":2500,"operations":2500,"ticks":3000,"server_runs":1000}
ALLOWED_INSTANCE_POLICIES={"IgnoreNew","Queue","Parallel","StopExisting","Unknown"}
ALLOWED_LOGON_TYPES={"Interactive","Password","S4U","Group","ServiceAccount",
                     "InteractiveOrPassword","None","Unknown"}
BLOCKED=re.compile(r"(?:https?://|\\\\|[A-Za-z]:[\\/]|(?:c_user|xs|cookie|password|token|secret)\s*[=:]|\b[^\s@]+@[^\s@]+\.[A-Za-z]{2,}\b)",re.I)

def check_string(v):
    if len(v)>200 or BLOCKED.search(v):
        raise ValueError("UNSAFE_STRING")
    if any(ord(ch)<32 for ch in v):
        raise ValueError("CONTROL_CHARACTER")

def validate_report(x):
    if not isinstance(x,dict) or set(x)-TOP:
        raise ValueError("UNEXPECTED_TOP_LEVEL_FIELD")
    if x.get("schema")!="facebook.forensic.v1" or x.get("provenance")!="local_sanitized_export_not_external_facebook_proof":
        raise ValueError("UNEXPECTED_SCHEMA")
    for key,allowed in FIELDS.items():
        rows=x.get(key,[])
        if not isinstance(rows,list) or len(rows)>ROW_LIMITS[key]:
            raise ValueError("TOO_MANY_ROWS")
        for row in rows:
            if not isinstance(row,dict) or set(row)-allowed:
                raise ValueError("UNEXPECTED_"+key.upper()+"_FIELD")
    from app.forensic_report import safe_code,ALLOWED_STAGES,ALLOWED_JOB_STATES
    for row in x.get("jobs",[]):
        if row.get("status") not in ALLOWED_JOB_STATES:
            raise ValueError("UNKNOWN_JOB_STATE")
    for row in x.get("operations",[]):
        if "stage" in row and row["stage"] not in ALLOWED_STAGES:
            raise ValueError("UNKNOWN_OPERATION_STAGE")
        if "error_code" in row and safe_code(row["error_code"])!=row["error_code"]:
            raise ValueError("UNKNOWN_OPERATION_ERROR_CODE")
    for row in x.get("server_runs",[]):
        if row.get("stage") not in {"SERVER_LOGON_START","SERVER_LOGON_END","SERVER_LOGON_FAILED"}:
            raise ValueError("UNKNOWN_SERVER_LOGON_STAGE")
    for row in x.get("ticks",[]):
        if row.get("stage") not in {"TICK_START","TICK_END","TICK_RESULT","TICK_EXCEPTION","FORENSICS_EXPORT_FAILED"}:
            raise ValueError("UNKNOWN_TICK_STAGE")
        if "error_code" in row and safe_code(row["error_code"])!=row["error_code"]:
            raise ValueError("UNKNOWN_TICK_ERROR_CODE")
    for row in x.get("job_events",[]):
        if "code" in row and safe_code(row["code"])!=row["code"]:
            raise ValueError("UNKNOWN_JOB_EVENT_CODE")
    if "plan" in x:
        plan=x["plan"]
        if not isinstance(plan,dict) or set(plan)-{"state","day","planned_jobs","expected_jobs","codes"}:
            raise ValueError("INVALID_PLAN_DIAGNOSTICS")
        if plan.get("state") not in {"CONFIG_MISSING","CONFIG_INVALID","PLAN_EMPTY","PLAN_MATCH","PLAN_CONFIG_DRIFT"}:
            raise ValueError("INVALID_PLAN_STATE")
        permitted={"PLAN_COUNT_MISMATCH","PLAN_GROUP_MISMATCH","PLAN_ACCOUNT_MISMATCH",
                   "PLAN_SLOT_MISMATCH","PLAN_DUE_MISMATCH","PLAN_GROUP_LIMIT_EXCEEDED",
                   "PLAN_SLOT_LIMIT_EXCEEDED"}
        if "codes" in plan and (not isinstance(plan["codes"],list) or
                               not set(plan["codes"]).issubset(permitted)):
            raise ValueError("INVALID_PLAN_CODES")
        for field in ("planned_jobs","expected_jobs"):
            if field in plan and (type(plan[field]) is not int or not 0<=plan[field]<=1200):
                raise ValueError("INVALID_PLAN_COUNT")
    if "windows" in x:
        w=x["windows"]
        if not isinstance(w,dict) or set(w)-WINDOWS:
            raise ValueError("UNEXPECTED_WINDOWS_FIELD")
        for row in w.get("recent_events",[]):
            if not isinstance(row,dict) or set(row)-{"event_id","at_utc"}:
                raise ValueError("UNEXPECTED_WINDOWS_EVENT_FIELD")
        if "event_log_status" in w and w["event_log_status"] not in {"OK","EMPTY","DISABLED","ERROR","UNKNOWN"}:
            raise ValueError("INVALID_WINDOWS_EVENT_LOG_STATUS")
        for key in ("server_logon_task_exists","forensic_sync_task_exists"):
            if key in w and type(w[key]) is not bool:
                raise ValueError("INVALID_WINDOWS_AUX_TASK_EXISTS")
        for key in ("server_logon_task_state","forensic_sync_task_state"):
            if key in w and w[key] not in {"Ready","Running","Disabled","Queued","Unknown"}:
                raise ValueError("INVALID_WINDOWS_AUX_TASK_STATE")
        if w.get("task_state") not in {"Ready","Running","Disabled","Queued","Unknown"}:
            raise ValueError("INVALID_WINDOWS_TASK_STATE")
        if "multiple_instances" in w and w["multiple_instances"] not in ALLOWED_INSTANCE_POLICIES:
            raise ValueError("INVALID_WINDOWS_INSTANCE_POLICY")
        if "logon_type" in w and w["logon_type"] not in ALLOWED_LOGON_TYPES:
            raise ValueError("INVALID_WINDOWS_LOGON_TYPE")
        for key,maximum in (("missed_runs",100000000),("execution_limit_minutes",1000000),
                            ("event_scan_count",1000000)):
            if key in w and w[key] is not None and (type(w[key]) is not int or not 0 <= w[key] <= maximum):
                raise ValueError("INVALID_WINDOWS_METRIC_"+key.upper())
        if "event_scan_truncated" in w and type(w["event_scan_truncated"]) is not bool:
            raise ValueError("INVALID_WINDOWS_SCAN_STATUS")
    # Todos os textos gerados são metadados curtos: nunca conteúdo livre.
    def inspect(o):
        if isinstance(o,str):check_string(o)
        elif isinstance(o,dict):
            for k,v in o.items():
                if not isinstance(k,str) or len(k)>80:raise ValueError("INVALID_FIELD")
                inspect(v)
        elif isinstance(o,list):
            for v in o:inspect(v)
        elif o is not None and type(o) not in (int,float,bool):
            raise ValueError("INVALID_TYPE")
    inspect(x)
    return True

def main(path):
    p=Path(path)
    if p.stat().st_size>4*1024*1024:raise ValueError("REPORT_TOO_LARGE")
    validate_report(json.loads(p.read_text(encoding="utf-8-sig")))
    print("REPORT_SCHEMA_APPROVED")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main(sys.argv[1]))
    except (IndexError,OSError,ValueError) as exc:
        print("REPORT_REJECTED_"+type(exc).__name__)
        raise SystemExit(2)
