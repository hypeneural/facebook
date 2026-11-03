"""Read-only forensic check of legacy/current SQLite relationships.

Never creates or migrates the DB. Output contains only counts and closed codes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3

TABLES={"jobs","jobs_v2","events"}
def audit(database):
    path=Path(database)
    if not path.is_file():
        return {"schema":"facebook.sqlite-relations.v1","status":"BLOCKED",
                "codes":["SQLITE_DATABASE_MISSING"],"counts":{}}
    codes=set()
    counts={}
    db=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=5)
    try:
        db.execute("PRAGMA query_only=ON")
        check=db.execute("PRAGMA integrity_check(1)").fetchone()
        if check is None or check[0]!="ok":
            codes.add("SQLITE_INTEGRITY_CHECK_FAILED")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            codes.add("SQLITE_FOREIGN_KEY_CHECK_FAILED")
        present={r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if not TABLES.issubset(present):
            codes.add("SQLITE_SCHEMA_INCOMPLETE")
        else:
            for name in ("jobs","jobs_v2","events"):
                counts[name]=db.execute("SELECT count(*) FROM "+name).fetchone()[0]
            counts["legacy_missing_in_v2"]=db.execute(
                "SELECT count(*) FROM jobs j WHERE NOT EXISTS"
                " (SELECT 1 FROM jobs_v2 v WHERE v.id=j.id)").fetchone()[0]
            counts["orphan_events"]=db.execute(
                "SELECT count(*) FROM events e WHERE NOT EXISTS"
                " (SELECT 1 FROM jobs_v2 v WHERE v.id=e.job_id)").fetchone()[0]
            counts["duplicate_operations"]=db.execute(
                "SELECT count(*) FROM (SELECT operation_id FROM jobs_v2 "
                "WHERE operation_id IS NOT NULL GROUP BY operation_id HAVING count(*)>1)"
                ).fetchone()[0]
            counts["unknown_job_states"]=db.execute(
                "SELECT count(*) FROM jobs_v2 WHERE status NOT IN"
                " ('PLANNED','NEEDS_REVIEW','MISSED','SKIPPED','VERIFIED_EXTERNALLY')"
                ).fetchone()[0]
            counts["pending_review"]=db.execute(
                "SELECT count(*) FROM jobs_v2 WHERE status='NEEDS_REVIEW'").fetchone()[0]
            if counts["legacy_missing_in_v2"]:
                codes.add("LEGACY_JOB_NOT_MIGRATED")
            if counts["orphan_events"]:
                codes.add("ORPHAN_JOB_EVENTS")
            if counts["duplicate_operations"]:
                codes.add("OPERATION_ID_REUSED")
            if counts["unknown_job_states"]:
                codes.add("INVALID_JOB_STATE")
            if counts["pending_review"]:
                codes.add("PENDING_PUBLICATION_REVIEW")
    except sqlite3.Error:
        codes.add("SQLITE_READ_FAILED")
    finally:
        db.close()
    hard={"SQLITE_INTEGRITY_CHECK_FAILED","SQLITE_FOREIGN_KEY_CHECK_FAILED","SQLITE_SCHEMA_INCOMPLETE",
          "LEGACY_JOB_NOT_MIGRATED","ORPHAN_JOB_EVENTS","OPERATION_ID_REUSED",
          "INVALID_JOB_STATE","SQLITE_READ_FAILED"}
    status="BLOCKED" if codes.intersection(hard) else ("PARTIAL" if codes else "PASS")
    return {"schema":"facebook.sqlite-relations.v1","status":status,
            "codes":sorted(codes),"counts":counts}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",type=Path,
        default=Path(__file__).resolve().parents[1]/"data"/"daily-queue.sqlite")
    args=parser.parse_args(argv)
    try:
        result=audit(args.db)
    except (OSError,sqlite3.Error,ValueError):
        result={"schema":"facebook.sqlite-relations.v1","status":"BLOCKED",
                "codes":["SQLITE_DATABASE_UNREADABLE"],"counts":{}}
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="PASS" else 3


if __name__=="__main__":
    raise SystemExit(main())
