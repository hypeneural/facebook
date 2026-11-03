"""Verify an existing local forensic backup without restoring or modifying it.

Never emits filenames, paths, secrets, content or SQLite row values.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sqlite3
from scripts.backup_forensics import sha256

ALLOWED={"daily-queue.sqlite","daily.json","groups.json","operations.jsonl",
         "history.jsonl","ticks.jsonl","server-logon.jsonl","forensic-identity.key"}
HEX=re.compile(r"^[0-9a-f]{64}$")


def verify(folder):
    folder=Path(folder)
    problems=set()
    try:
        manifest_path=folder/"manifest.json"
        if manifest_path.is_symlink():
            raise ValueError("BACKUP_MANIFEST_SYMLINK")
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema")!="facebook.local-backup.v1":
            raise ValueError("BACKUP_SCHEMA_INVALID")
        rows=manifest.get("files")
        if not isinstance(rows,list):
            raise ValueError("BACKUP_ENTRIES_INVALID")
        observed=set()
        for row in rows:
            if not isinstance(row,dict) or set(row)!={"file","bytes","sha256"}:
                problems.add("BACKUP_ENTRY_INVALID")
                continue
            name=row["file"]
            if not isinstance(name,str) or name not in ALLOWED or name in observed:
                problems.add("BACKUP_ENTRY_INVALID")
                continue
            observed.add(name)
            entry=folder/name
            if entry.is_symlink() or not entry.is_file():
                problems.add("BACKUP_FILE_MISSING")
                continue
            if type(row["bytes"]) is not int or row["bytes"]<0 or not isinstance(row["sha256"],str) or not HEX.fullmatch(row["sha256"]):
                problems.add("BACKUP_ENTRY_INVALID")
                continue
            if entry.stat().st_size!=row["bytes"] or sha256(entry)!=row["sha256"]:
                problems.add("BACKUP_HASH_MISMATCH")
            if name=="daily-queue.sqlite":
                try:
                    con=sqlite3.connect(entry.resolve().as_uri()+"?mode=ro",uri=True,timeout=3)
                    try:
                        quick=con.execute("PRAGMA quick_check(1)").fetchone()
                        if not quick or quick[0]!="ok":
                            problems.add("BACKUP_SQLITE_CORRUPT")
                    finally:con.close()
                except sqlite3.Error:
                    problems.add("BACKUP_SQLITE_CORRUPT")
        if "daily-queue.sqlite" not in observed:
            problems.add("BACKUP_SQLITE_NOT_INCLUDED")
    except (OSError,ValueError,TypeError,json.JSONDecodeError):
        problems.add("BACKUP_MANIFEST_INVALID")
    return {"schema":"facebook.backup-check.v1",
            "status":"BLOCKED" if problems else "PASS",
            "codes":sorted(problems)}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    a=p.parse_args(argv)
    result=verify(a.folder)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="PASS" else 3


if __name__=="__main__":
    raise SystemExit(main())
