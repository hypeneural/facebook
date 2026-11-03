"""SQLite relation diagnostics must be read-only, preserve DB bytes and avoid IDs."""
import json
import sqlite3
from scripts.audit_sqlite_relations import audit
from app.daily_queue import DailyQueue


def test_missing_db_does_not_create_file(tmp_path):
    db=tmp_path/"missing.sqlite"
    result=audit(db)
    assert result["status"]=="BLOCKED"
    assert result["codes"]==["SQLITE_DATABASE_MISSING"]
    assert not db.exists()


def test_clean_database_has_consistent_relationships(tmp_path):
    db=tmp_path/"clean.sqlite"
    q=DailyQueue(db)
    q.close()
    result=audit(db)
    assert result["status"]=="PASS"
    assert result["counts"]=={"jobs":0,"jobs_v2":0,"events":0,
        "legacy_missing_in_v2":0,"orphan_events":0,"duplicate_operations":0,
        "unknown_job_states":0,"pending_review":0}


def test_orphan_events_block_without_modifying_db(tmp_path):
    db=tmp_path/"orphan.sqlite"
    q=DailyQueue(db)
    q.db.execute(
        "INSERT INTO events(at,job_id,event,code) VALUES(?,?,?,?)",
        ("2026-11-02T10:00:00+00:00","an-unknown-job","PREFLIGHT_FAILED","SERVER_NOT_READY"))
    q.db.commit()
    q.close()
    before=db.read_bytes()
    result=audit(db)
    assert result["status"]=="BLOCKED"
    assert "ORPHAN_JOB_EVENTS" in result["codes"]
    assert result["counts"]["orphan_events"]==1
    assert db.read_bytes()==before
    assert "an-unknown-job" not in json.dumps(result)


def test_legacy_missing_v2_is_reported_but_never_auto_imported(tmp_path):
    db=tmp_path/"partial.sqlite"
    q=DailyQueue(db)
    q.db.execute(
        "INSERT INTO jobs(id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,"
        "manifest_sha256,status) VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("oldjob","2026-11-02","08:00","2026-11-02T11:00:00+00:00",
         "principal","12345","photo","text","0"*64,"NEEDS_REVIEW"))
    q.db.commit()
    q.close()
    result=audit(db)
    assert result["counts"]["legacy_missing_in_v2"]==1
    assert "LEGACY_JOB_NOT_MIGRATED" in result["codes"]


def test_uncertain_job_is_partial_not_requeued(tmp_path):
    db=tmp_path/"review.sqlite"
    q=DailyQueue(db)
    q.db.execute(
        "INSERT INTO jobs_v2(id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,"
        "manifest_sha256,status) VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("item1","2026-11-02","08:00","2026-11-02T11:00:00+00:00",
         "principal","12345","photo","text","0"*64,"NEEDS_REVIEW"))
    q.db.commit()
    q.close()
    result=audit(db)
    assert result["status"]=="PARTIAL"
    assert "PENDING_PUBLICATION_REVIEW" in result["codes"]
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT status FROM jobs_v2").fetchone()[0]=="NEEDS_REVIEW"
