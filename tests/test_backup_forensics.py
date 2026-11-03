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


def test_backup_covers_campaign_config_and_verifies_hashes(tmp_path):
    from scripts.verify_backup_forensics import verify
    data=tmp_path/"data"
    data.mkdir()
    with sqlite3.connect(data/"daily-queue.sqlite") as db:
        db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY)")
    (data/"daily.json").write_text('{"enabled":false}',encoding="utf-8")
    (data/"groups.json").write_text('[{"name":"Private group"}]',encoding="utf-8")
    output=data/"backups"/"transaction"
    result=backup(data,output)
    assert result["files"]==3
    assert verify(output)["status"]=="PASS"
    files={r["file"] for r in json.loads((output/"manifest.json").read_text())["files"]}
    assert files=={"daily-queue.sqlite","daily.json","groups.json"}


def test_backup_verification_detects_tampering_without_data_leak(tmp_path):
    from scripts.verify_backup_forensics import verify
    data=tmp_path/"data"
    data.mkdir()
    with sqlite3.connect(data/"daily-queue.sqlite") as db:
        db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY)")
    output=data/"backups"/"transaction"
    backup(data,output)
    (output/"daily-queue.sqlite").write_bytes(b"SECRET_PERSONAL_CONTENT")
    result=verify(output)
    assert result["status"]=="BLOCKED"
    assert "BACKUP_HASH_MISMATCH" in result["codes"]
    assert "SECRET_PERSONAL_CONTENT" not in json.dumps(result)


def test_backup_rejects_config_symlinks(tmp_path):
    import pytest
    data=tmp_path/"data"
    data.mkdir()
    outside=tmp_path/"secret.json"
    outside.write_text('{"secret":true}',encoding="utf-8")
    try:
        (data/"daily.json").symlink_to(outside)
    except (OSError,NotImplementedError):
        pytest.skip("Symlink creation unsupported in this runner")
    with pytest.raises(RuntimeError,match="BACKUP_SOURCE_SYMLINK_REJECTED"):
        backup(data,data/"backups"/"transaction")
