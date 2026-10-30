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

def read_jsonl(path,limit=3000):
    if not path.is_file():return []
    # Tratar histórico grande sem carregar o arquivo inteiro em memória.
    from collections import deque
    rows=deque(maxlen=limit)
    with path.open("r",encoding="utf-8",errors="replace") as fd:
        for line in fd:
            try:
                row=json.loads(line)
                if isinstance(row,dict):rows.append(row)
            except (ValueError,TypeError):
                continue
    return list(rows)

def collect(data_dir):
    jobs=[]
    events=[]
    db_path=data_dir/"daily-queue.sqlite"
    if db_path.is_file():
        # Snapshot read-only, nunca executar WAL checkpoint nem mudar esquema.
        con=sqlite3.connect(db_path.resolve().as_uri()+"?mode=ro",uri=True,timeout=5)
        try:
            con.row_factory=sqlite3.Row
            con.execute("PRAGMA query_only=ON")
            rows=con.execute("SELECT * FROM jobs_v2 ORDER BY due_utc,id LIMIT 15000")
            jobs=[dict(v) for v in rows]
            events=[dict(v) for v in con.execute(
                "SELECT job_id,at,event,code FROM events ORDER BY id DESC LIMIT 5000")]
            events.reverse()
        finally:con.close()
    windows=None
    winfile=data_dir/"diagnostics"/"windows.json"
    if winfile.is_file():
        try:windows=json.loads(winfile.read_text(encoding="utf-8"))
        except (OSError,ValueError):windows=None
    return summarize(jobs,events,read_jsonl(data_dir/"operations.jsonl"),windows,
                     read_jsonl(data_dir/"diagnostics"/"ticks.jsonl"))

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
