from pathlib import Path
import json
import sqlite3
from scripts.backup_forensics import backup, sha256

def test_local_backup_is_transactional_and_does_not_copy_chrome(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    db=data/"daily-queue.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, state TEXT)")
        conn.execute("INSERT INTO evidence(state) VALUES('NEEDS_REVIEW')")
    (data/"operations.jsonl").write_text('{"stage":"SUBMITTED_UNVERIFIED"}\n',encoding="utf8")
    profile=data/"chrome-profile"
    profile.mkdir()
    (profile/"Cookies").write_text("SECRET_COOKIE",encoding="utf8")
    target=data/"backups"/"snapshot_manual"
    result=backup(data,target)
    assert result["files"]==2
    with sqlite3.connect(target/"daily-queue.sqlite") as conn:
        assert conn.execute("SELECT state FROM evidence").fetchone()[0]=="NEEDS_REVIEW"
    assert not (target/"Cookies").exists()
    assert "SECRET_COOKIE" not in (target/"manifest.json").read_text()
    manifest=json.loads((target/"manifest.json").read_text())
    assert manifest["files"][0]["sha256"]==sha256(target/"daily-queue.sqlite")
