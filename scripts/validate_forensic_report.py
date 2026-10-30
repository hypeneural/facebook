"""Valida e bloqueia conteúdo inesperado antes de qualquer commit no GitHub.

Somente snapshots gerados pela ferramenta de exportação são aceitáveis.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

TOP={"schema","generated_at","provenance","totals","jobs","job_events","operations",
     "windows","ticks","build_revision","runtime","collection_errors"}
FIELDS={
 "jobs":{"job_id","status","account_id_hash","group_id_hash","creative_id_hash",
         "caption_id_hash","day","slot","due_utc","checked_at","operation_id"},
 "job_events":{"job_id","at","event","code"},
 "operations":{"operation_id","job_id","account_id_hash","group_id_hash",
               "at","stage","media_count","bytes_total","duration_ms",
               "observed_count","overflow_count","status","post_ui_state",
               "media_kind","upload_method","error_code","error_class",
               "source_file","source_line"},
 "ticks":{"run_id","stage","at","pid","exit_code","duration_ms","error_class"},
}
WINDOWS={"schema","os_family","task_exists","task_state","last_result_code",
         "recent_scheduler_event_ids","recent_events","collection_errors"}
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
        if not isinstance(rows,list) or len(rows)>2500:
            raise ValueError("TOO_MANY_ROWS")
        for row in rows:
            if not isinstance(row,dict) or set(row)-allowed:
                raise ValueError("UNEXPECTED_"+key.upper()+"_FIELD")
    if "windows" in x:
        w=x["windows"]
        if not isinstance(w,dict) or set(w)-WINDOWS:
            raise ValueError("UNEXPECTED_WINDOWS_FIELD")
        for row in w.get("recent_events",[]):
            if not isinstance(row,dict) or set(row)-{"event_id","at_utc"}:
                raise ValueError("UNEXPECTED_WINDOWS_EVENT_FIELD")
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
