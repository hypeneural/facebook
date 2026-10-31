"""Wrapper Task Scheduler: registra início/fim em arquivo local append-only.

Não registra arguments, legendas, URLs, tokens, caminhos nem exceção em texto.
"""
from __future__ import annotations
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import daily_tick

def record(stage,run_id,**extra):
    path=ROOT/"data"/"diagnostics"/"ticks.jsonl"
    path.parent.mkdir(parents=True,exist_ok=True)
    event={"at":datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
           "run_id":run_id,"stage":stage,"pid":os.getpid(),**extra}
    data=(json.dumps(event,separators=(",",":"))+"\n").encode("utf8")
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_APPEND|getattr(os,"O_BINARY",0),0o600)
    try:
        if os.write(fd,data)!=len(data):raise OSError("short write")
        os.fsync(fd)
    finally:os.close(fd)

def snapshot(run_id):
    """Gera relatório sintético versionável, mas NUNCA realiza push por conta própria."""
    try:
        from scripts.export_forensics import collect
        from app.daily_queue import TIMEZONE
        report=collect(ROOT/"data")
        out=ROOT/"reports"/"forensic"
        out.mkdir(parents=True,exist_ok=True)
        day=datetime.now(TIMEZONE).date().isoformat()
        target=out/(day+".json")
        temp=target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf8")
        temp.replace(target)
    except Exception as exc:
        record("FORENSICS_EXPORT_FAILED",run_id,error_class=type(exc).__name__[:60])

def main():
    run_id=str(uuid.uuid4())
    started=time.monotonic()
    record("TICK_START",run_id)
    previous=os.environ.get("EVYD_FORENSIC_RUN_ID")
    os.environ["EVYD_FORENSIC_RUN_ID"]=run_id
    try:
        code=daily_tick.main()
        if type(code) is not int:code=2
        record("TICK_END",run_id,exit_code=code,duration_ms=int(1000*(time.monotonic()-started)))
        snapshot(run_id)
        return code
    except BaseException as exc:
        # Falha inesperada: classe da exceção apenas, não o texto com paths/credenciais.
        record("TICK_EXCEPTION",run_id,error_class=type(exc).__name__[:60],
               duration_ms=int(1000*(time.monotonic()-started)))
        snapshot(run_id)
        raise
    finally:
        # Never leave a stale execution id in a long-lived interpreter/test runner.
        if previous is None:
            os.environ.pop("EVYD_FORENSIC_RUN_ID",None)
        else:
            os.environ["EVYD_FORENSIC_RUN_ID"]=previous

if __name__=="__main__":
    raise SystemExit(main())
