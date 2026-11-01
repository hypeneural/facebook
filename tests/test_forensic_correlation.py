import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.telemetry import AuditTrail
from app.forensic_report import sanitize_operation
from app import main

def test_server_event_has_job_correlation(tmp_path):
    op=str(uuid4())
    jid="b8a9a960b1aa21a855ab94c1dd870d26"
    trail=AuditTrail(tmp_path)
    trail.emit(op,"REQUEST_ACCEPTED",job_id=jid,group_id="389335997243726",durable=True)
    event=trail.recent()[0]["events"][0]
    assert event["job_id"]==jid
    safe=sanitize_operation(event)
    assert safe["job_id"]==jid
    assert safe["group_id_hash"]
    assert "group_id" not in safe

def test_publish_rejects_invalid_scheduler_id():
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as client:
        r=client.post("/api/publish",data={
             "group_url":"https://www.facebook.com/groups/123456/",
             "caption":"Teste","job_id":"../../malicious"})
        assert r.status_code==422

def test_no_job_id_remains_compatible():
    op=str(uuid4())
    safe=sanitize_operation({"operation_id":op,"stage":"REQUEST_ACCEPTED",
        "group_id":"123456"})
    assert safe["operation_id"]==op
    assert "job_id" not in safe
