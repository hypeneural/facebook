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
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
    try:
        if os.write(fd,data)!=len(data):raise OSError("short write")
        os.fsync(fd)
    finally:os.close(fd)

def main():
    run_id=str(uuid.uuid4())
    started=time.monotonic()
    record("TICK_START",run_id)
    try:
        code=daily_tick.main()
        if type(code) is not int:code=2
        record("TICK_END",run_id,exit_code=code,duration_ms=int(1000*(time.monotonic()-started)))
        return code
    except BaseException as exc:
        # Falha inesperada: classe da exceção apenas, não o texto com paths/credenciais.
        record("TICK_EXCEPTION",run_id,error_class=type(exc).__name__[:60],
               duration_ms=int(1000*(time.monotonic()-started)))
        raise

if __name__=="__main__":
    raise SystemExit(main())
