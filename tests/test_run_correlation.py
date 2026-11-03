"""Regressões de correlação e segurança do executor de janelas Windows."""
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app import main as api
from app.forensic_report import sanitize_operation, sanitize_tick, summarize
from scripts import daily_tick
from scripts.validate_forensic_report import validate_report


def test_tick_result_persists_run_and_job(tmp_path, monkeypatch):
    run_id=str(uuid4())
    job_id="b8a9a960b1aa21a855ab94c1dd870d26"
    operation_id=str(uuid4())
    monkeypatch.setenv("EVYD_FORENSIC_RUN_ID",run_id)
    monkeypatch.setattr(daily_tick,"ROOT",tmp_path)
    daily_tick.audit_tick_result({
        "state":"NEEDS_REVIEW","job_id":job_id,
        "operation_id":operation_id,"outcome":"SUBMITTED_UNVERIFIED",
        "caption":"never log caption","password":"never log password"})
    rows=(tmp_path/"data"/"diagnostics"/"ticks.jsonl").read_text().splitlines()
    assert len(rows)==1
    item=json.loads(rows[0])
    assert item["run_id"]==run_id and item["job_id"]==job_id
    assert item["operation_id"]==operation_id
    assert "caption" not in rows[0] and "password" not in rows[0]
    report=summarize([],[],[],raw_ticks=[item])
    assert report["ticks"][0]["job_id"]==job_id
    assert report["ticks"][0]["operation_id"]==operation_id
    assert validate_report(report) is True


def test_no_env_never_writes_tick_result(tmp_path,monkeypatch):
    monkeypatch.delenv("EVYD_FORENSIC_RUN_ID",raising=False)
    monkeypatch.setattr(daily_tick,"ROOT",tmp_path)
    daily_tick.audit_tick_result({"state":"NO_DUE_WORK"})
    assert not (tmp_path/"data"/"diagnostics"/"ticks.jsonl").exists()


def test_remote_request_run_id_is_rejected_before_browser(tmp_path):
    with TestClient(api.app,base_url="http://127.0.0.1:8108") as client:
        result=client.post("/api/publish",data={
            "group_url":"https://www.facebook.com/groups/123456/",
            "caption":"Offline validation","run_id":"../../spoof"})
        assert result.status_code==422


def test_operation_export_has_safely_validated_run_id():
    uid=str(uuid4())
    op=str(uuid4())
    item=sanitize_operation({"operation_id":op,"run_id":uid,"stage":"REQUEST_ACCEPTED",
                             "caption":"DO_NOT_EXPORT","group_id":"123456"})
    assert item["run_id"]==uid
    assert "caption" not in item and "group_id" not in item
    assert sanitize_operation({"operation_id":op,"run_id":"bad/token"})["operation_id"]==op
    assert "run_id" not in sanitize_operation({"operation_id":op,"run_id":"bad/token"})


def test_multipart_propagates_same_run_and_job(monkeypatch):
    sent=[]
    class Response:
        status=200
        def read(self,n):return b'{"status":"SUBMITTED_UNVERIFIED"}'
    class FakeConnection:
        def __init__(self,*args,**kwargs):pass
        def putrequest(self,*args):pass
        def putheader(self,*args):pass
        def endheaders(self):pass
        def send(self,part):sent.append(part)
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(daily_tick.http.client,"HTTPConnection",FakeConnection)
    run_id=str(uuid4())
    monkeypatch.setenv("EVYD_FORENSIC_RUN_ID",run_id)
    job_id="b8a9a960b1aa21a855ab94c1dd870d26"
    result=daily_tick.send_multipart("https://www.facebook.com/groups/123456/","Preview",[],job_id=job_id)
    payload=b"".join(sent)
    assert result["status"]=="SUBMITTED_UNVERIFIED"
    assert b'name="run_id"' in payload and run_id.encode() in payload
    assert b'name="job_id"' in payload and job_id.encode() in payload
