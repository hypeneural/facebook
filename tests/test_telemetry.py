"""Eventos sanitizados e ciclo de vida offline (nenhum navegador ou Facebook)."""
from app.telemetry import AuditTrail,error_code,group_id
import json
import pytest

def test_event_chain_sanitized(tmp_path):
    audit=AuditTrail(tmp_path)
    audit.emit("abc","REQUEST_ACCEPTED",account_id="principal",group_id="1234",media_count=2)
    audit.emit("abc","FILES_STAGED",bytes_total=230000,media_kind="image")
    audit.emit("abc","SUBMIT_INTENT",durable=True,status="SUBMITTED_UNVERIFIED")
    rows=audit.recent()
    assert len(rows)==1
    assert [e["stage"] for e in rows[0]["events"]]==["REQUEST_ACCEPTED","FILES_STAGED","SUBMIT_INTENT"]
    assert audit.submitted_intent_exists("abc") is True
    assert rows[0]["media_count"]==2
    raw=(tmp_path/"operations.jsonl").read_text(encoding="utf8")
    assert "password" not in raw and "cookie" not in raw

def test_sensitive_fields_never_written(tmp_path):
    audit=AuditTrail(tmp_path)
    with pytest.raises(ValueError):
        audit.emit("abc","BAD",caption="private marketing text")
    assert not audit.path.exists()

def test_group_id_and_error_categories():
    assert group_id("https://www.facebook.com/groups/464027871072447/")=="464027871072447"
    assert group_id("https://facebook.com/pages/1") is None
    assert error_code("MEDIA_PREVIEW","Não foi possível comprovar prévia nova")=="MEDIA_PREVIEW_UNVERIFIED"
    assert error_code("NAVIGATE","checkpoint")=="FACEBOOK_RESTRICTED"
    assert error_code("COMPOSER","timeout")=="TIMEOUT_AT_COMPOSER"

def test_empty_and_unresolved(tmp_path):
    a=AuditTrail(tmp_path)
    assert a.recent()==[]
    assert not a.submitted_intent_exists("unknown")
    a.emit("first","PRE_SUBMIT_FAILED",status="FAILED_BEFORE_SUBMIT")
    assert not a.submitted_intent_exists("first")
