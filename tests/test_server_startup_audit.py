"""Snapshot of server startup is safe to publish and correlated by run id."""
from uuid import uuid4
from app.forensic_report import summarize
from scripts.validate_forensic_report import validate_report
import pytest


def test_server_startup_telemetry_is_sanitized():
    uid=str(uuid4())
    report=summarize([],[],[],raw_server_runs=[
       {"stage":"SERVER_LOGON_START","run_id":uid,
        "at":"2026-10-31T01:00:00+00:00","exit_code":0},
       {"stage":"SERVER_LOGON_FAILED","run_id":uid,"exit_code":4,
        "error_class":"RuntimeException","path":"C:/PRIVATE","cookie":"DO_NOT_EXPORT"}])
    assert len(report["server_runs"])==2
    assert report["server_runs"][1]["error_class"]=="RuntimeException"
    assert "PRIVATE" not in str(report)
    assert "DO_NOT_EXPORT" not in str(report)
    assert validate_report(report) is True


def test_bad_server_logon_stage_rejected():
    report=summarize([],[],[],raw_server_runs=[{
        "stage":"SERVER_LOGON_END","run_id":str(uuid4())}])
    report["server_runs"][0]["stage"]="cookie=secret"
    with pytest.raises(ValueError):
        validate_report(report)
