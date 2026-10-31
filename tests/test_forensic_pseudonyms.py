"""Ensure public forensic snapshots cannot reverse common numeric group IDs."""
import json
import pytest
from app.forensic_report import digest_id, summarize
from scripts.export_forensics import load_local_identity_key, collect


def test_hmac_pseudonyms_stable_per_local_install(tmp_path):
    key=load_local_identity_key(tmp_path)
    assert len(key)==32
    assert key==load_local_identity_key(tmp_path)
    a=digest_id("123456789",identity_key=key)
    b=digest_id("123456789",identity_key=key)
    assert a==b and a!=digest_id("123456789")
    other=digest_id("123456789",identity_key=b"Z"*32)
    assert a!=other
    assert (tmp_path/"diagnostics"/"forensic-identity.key").read_bytes()==key


def test_export_creates_key_not_in_snapshot(tmp_path):
    report=collect(tmp_path)
    assert report["schema"]=="facebook.forensic.v1"
    assert (tmp_path/"diagnostics"/"forensic-identity.key").exists()
    assert "forensic-identity.key" not in json.dumps(report)
    assert load_local_identity_key(tmp_path).hex() not in json.dumps(report)


def test_corrupt_key_refuses_unkeyed_fallback(tmp_path):
    directory=tmp_path/"diagnostics"
    directory.mkdir()
    (directory/"forensic-identity.key").write_bytes(b"invalid")
    with pytest.raises(RuntimeError,match="FORENSIC_IDENTITY_KEY_CORRUPT"):
        collect(tmp_path)


def test_snapshot_uses_salted_group_hash():
    row={"operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
         "stage":"REQUEST_ACCEPTED","group_id":"123456789"}
    report=summarize([],[],[row],identity_key=b"A"*32)
    op=report["operations"][0]
    assert op["group_id_hash"]==digest_id("123456789",identity_key=b"A"*32)
    assert op["group_id_hash"]!=digest_id("123456789")


def test_job_id_pseudonym_links_operations_ticks_and_events():
    jid="b8a9a960b1aa21a855ab94c1dd870d26"
    uid="627b4aa2-efa7-42e6-916a-24a408ce00aa"
    key=b"Q"*32
    report=summarize(
        [{"id":jid,"status":"NEEDS_REVIEW"}],
        [{"job_id":jid,"event":"MISSED","code":"MISSED_WINDOW"}],
        [{"operation_id":uid,"stage":"REQUEST_ACCEPTED","job_id":jid}],
        raw_ticks=[{"stage":"TICK_RESULT","run_id":uid,"job_id":jid,"state":"NEEDS_REVIEW"}],
        identity_key=key)
    pseudonym=report["jobs"][0]["job_id"]
    assert pseudonym!=jid and len(pseudonym)==32
    assert report["job_events"][0]["job_id"]==pseudonym
    assert report["operations"][0]["job_id"]==pseudonym
    assert report["ticks"][0]["job_id"]==pseudonym
