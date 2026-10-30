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

def test_durable_marker_outlives_jsonl_pruning(tmp_path):
    audit=AuditTrail(tmp_path)
    op="a"*32
    audit.mark_submit_intent(op)
    assert audit.submitted_intent_exists(op)
    assert (tmp_path/"submit-intents"/op).is_file()

def test_recommendations_are_conservative(tmp_path):
    from app.telemetry import next_action
    a=AuditTrail(tmp_path)
    a.emit("x","SUBMIT_INTENT",status="SUBMITTED_UNVERIFIED")
    row=a.recent()[0]
    assert next_action(row)=="VERIFICAR_NO_GRUPO_SEM_REENVIAR"
    b={"events":[{"stage":"PRE_SUBMIT_FAILED"}],"error_code":"MEDIA_PREVIEW_UNVERIFIED"}
    assert next_action(b)=="INSPECIONAR_MIDIA_SEM_PUBLICAR"

def test_tail_only_recent_lines(tmp_path):
    a=AuditTrail(tmp_path)
    with a.path.open("wb") as f:
        f.write(b"x"*1024*1024+b"\n")
    a.emit("last","FILES_STAGED",media_count=2)
    assert a.recent()[0]["operation_id"]=="last"
