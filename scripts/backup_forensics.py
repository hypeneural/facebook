"""Cópia local transacional de auditoria. Nunca gera dados para Git.

O banco é preservado via sqlite3.backup, incluindo transações confirmadas em WAL.
Logs append-only são copiados como evidência, sem cookies ou perfil do navegador.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

ROOT=Path(__file__).resolve().parents[1]

def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as fd:
        while block:=fd.read(1024*1024):
            digest.update(block)
    return digest.hexdigest()

def backup(data_dir,output_dir=None):
    data_dir=Path(data_dir)
    output_dir=Path(output_dir or data_dir/"backups"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    if output_dir.exists():raise ValueError("BACKUP_DESTINATION_ALREADY_EXISTS")
    output_dir.mkdir(parents=True)
    records=[]
    original=data_dir/"daily-queue.sqlite"
    if original.exists():
        src=sqlite3.connect(original.resolve().as_uri()+"?mode=ro",uri=True,timeout=5)
        try:
            dstpath=output_dir/"daily-queue.sqlite"
            dst=sqlite3.connect(dstpath)
            try:src.backup(dst,pages=128,sleep=0.1)
            finally:dst.close()
            records.append({"file":"daily-queue.sqlite","bytes":dstpath.stat().st_size,
                            "sha256":sha256(dstpath)})
        finally:src.close()
    paths=[
      (data_dir/"operations.jsonl","operations.jsonl"),
      (data_dir/"history.jsonl","history.jsonl"),
      (data_dir/"diagnostics"/"ticks.jsonl","ticks.jsonl"),
      (data_dir/"diagnostics"/"server-logon.jsonl","server-logon.jsonl"),
      (data_dir/"diagnostics"/"forensic-identity.key","forensic-identity.key"),
    ]
    for source,name in paths:
        if source.is_file():
            target=output_dir/name
            with source.open("rb") as r,target.open("wb") as w:
                shutil.copyfileobj(r,w,length=1024*1024)
            records.append({"file":name,"bytes":target.stat().st_size,"sha256":sha256(target)})
    (output_dir/"manifest.json").write_text(json.dumps({
        "schema":"facebook.local-backup.v1",
        "created_at":datetime.now(timezone.utc).isoformat(),
        "files":records},indent=2)+"\n",encoding="utf8")
    return {"files":len(records),"backup_dir":output_dir}

if __name__=="__main__":
    result=backup(ROOT/"data")
    print(json.dumps({"state":"BACKUP_CREATED","files":result["files"],
      "destination":"LOCAL_DATA_BACKUPS_ONLY"}))
