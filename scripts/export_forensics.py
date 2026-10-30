"""Gera instantâneo Git-safe da telemetria, nunca cópia de logs brutos.

Ex.: python scripts/export_forensics.py --date 2026-10-30
Grava reports/forensic/<date>.json (versionável). Nenhum git push automático.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.forensic_report import summarize

def read_jsonl(path,limit=3000,tail_bytes=16*1024*1024):
    if not path.is_file():return []
    # Export recorrente limitado à cauda dos logs; logs e backups brutos não são removidos.
    from collections import deque
    import os
    rows=deque(maxlen=limit)
    with path.open("rb") as fd:
        fd.seek(0,os.SEEK_END)
        length=fd.tell()
        start=max(0,length-tail_bytes)
        fd.seek(start)
        if start:
            fd.readline()  # descarta linha parcial no limite da janela
        for raw in fd:
            try:
                row=json.loads(raw.decode("utf-8",errors="replace"))
                if isinstance(row,dict):rows.append(row)
            except (ValueError,TypeError):
                continue
    return list(rows)

def collect(data_dir):
    jobs=[]
    events=[]
    problems=[]
    db_path=data_dir/"daily-queue.sqlite"
    if db_path.is_file():
        try:
            con=sqlite3.connect(db_path.resolve().as_uri()+"?mode=ro",uri=True,timeout=5)
            try:
                con.row_factory=sqlite3.Row
                con.execute("PRAGMA query_only=ON")
                integrity=con.execute("PRAGMA quick_check(1)").fetchone()
                if integrity is None or integrity[0]!="ok":
                    problems.append("SQLITE_QUICK_CHECK_FAILED")
                jobs=[dict(v) for v in con.execute(
                    "SELECT * FROM jobs_v2 ORDER BY due_utc,id LIMIT 15000")]
                events=[dict(v) for v in con.execute(
                    "SELECT job_id,at,event,code FROM events ORDER BY id DESC LIMIT 5000")]
                events.reverse()
            finally:
                con.close()
        except (sqlite3.Error,OSError,ValueError):
            problems.append("SQLITE_READ_FAILED")
    windows=None
    winfile=data_dir/"diagnostics"/"windows.json"
    if winfile.is_file():
        try:windows=json.loads(winfile.read_text(encoding="utf-8-sig"))
        except (OSError,ValueError):
            problems.append("WINDOWS_DIAGNOSTICS_UNREADABLE")
    result=summarize(jobs,events,read_jsonl(data_dir/"operations.jsonl"),windows,
                     read_jsonl(data_dir/"diagnostics"/"ticks.jsonl"))
    import subprocess
    import platform
    try:
        revision=subprocess.run(["git","rev-parse","--short=12","HEAD"],cwd=ROOT,
            check=True,capture_output=True,text=True,timeout=3).stdout.strip()
        if not revision or len(revision)>12 or any(c not in "0123456789abcdef" for c in revision):
            revision=None
    except (OSError,subprocess.SubprocessError):
        revision=None
    result["build_revision"]=revision
    result["runtime"]={"python":f"{sys.version_info.major}.{sys.version_info.minor}",
                       "platform":platform.system()}
    result["collection_errors"]=sorted(set(problems))
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default=datetime.now().date().isoformat(),
                        help="Nome do snapshot, YYYY-MM-DD")
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"reports"/"forensic")
    args=parser.parse_args()
    from datetime import date
    date.fromisoformat(args.date)
    if not args.data_dir.exists():
        raise SystemExit("DATA_DIR_MISSING: não inventar relatório vazio")
    report=collect(args.data_dir)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    path=args.output_dir/(args.date+".json")
    tmp=path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(path)
    print(json.dumps({"state":"REPORT_CREATED","relative_file":str(path.relative_to(ROOT))
      if path.is_relative_to(ROOT) else "<external>","jobs":report["totals"]["jobs"],
       "operations":report["totals"]["operations"]},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
