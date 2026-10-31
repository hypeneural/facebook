"""Read-only, no-browser schedule inspector for Windows installer and operator.

Never calls DailyQueue(...) because its constructor creates/migrates SQLite.
Only stable diagnostic codes and counts are printed (no group IDs or captions).
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.daily_queue import TIMEZONE,inspect_day_plan


def read_existing_jobs(database:Path,day):
    """Read only: never create a SQLite DB, migrate tables, or freeze the day."""
    rows=[]
    if database.is_file():
        con=sqlite3.connect(database.resolve().as_uri()+"?mode=ro",uri=True,timeout=3)
        try:
            con.row_factory=sqlite3.Row
            con.execute("PRAGMA query_only=ON")
            rows=[dict(r) for r in con.execute(
                "SELECT day,slot,due_utc,account_id,group_id,status FROM jobs_v2 WHERE day=?",
                (day.isoformat(),))]
        finally:
            con.close()
    return rows


def inspect(config:Path,database:Path,day):
    cfg=json.loads(config.read_text(encoding="utf-8-sig"))
    return inspect_day_plan(cfg,read_existing_jobs(database,day),day)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=ROOT/"data"/"daily.json")
    parser.add_argument("--db",type=Path,default=ROOT/"data"/"daily-queue.sqlite")
    parser.add_argument("--date",default=None)
    args=parser.parse_args(argv)
    if not args.config.is_file():
        print(json.dumps({"state":"CONFIG_MISSING"}))
        return 2
    try:
        today=datetime.now(TIMEZONE).date()
        from datetime import date
        day=date.fromisoformat(args.date) if args.date else today
        result=inspect(args.config,args.db,day)
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        print(json.dumps({"state":"PLAN_INSPECTION_FAILED"}))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 3 if result["state"]=="PLAN_CONFIG_DRIFT" else 0


if __name__=="__main__":
    raise SystemExit(main())
