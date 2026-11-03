"""Readiness checks detect stale reports without inventing evidence of post success."""
import json
from datetime import datetime, timedelta, timezone
from app.forensic_report import summarize
from scripts.validate_operational_readiness import evaluate,main


NOW=datetime(2026,11,2,21,0,tzinfo=timezone.utc)


def report(*,generated=None,task=False,logon=False,plan="PLAN_EMPTY",ticks=None,server=None):
    value=summarize([],[],[],{
        "schema":"facebook.win11.v1",
        "task":{"exists":task,"state":"Ready","last_result_code":"0",
                "multiple_instances":"IgnoreNew","logon_type":"Interactive"},
        "server_logon_task_exists":logon,"forensic_sync_task_exists":False,
        "event_log_status":"DISABLED","errors":["EVENT_LOG_DISABLED"]},
        raw_ticks=ticks or [],raw_server_runs=server or [])
    value["generated_at"]=(generated or NOW).isoformat()
    value["plan"]={"state":plan,"day":"2026-11-02",
                   "planned_jobs":0,"expected_jobs":5,"codes":[]}
    value["collection_errors"]=["EVENT_LOG_DISABLED"]
    return value


def test_fresh_report_without_tasks_is_not_ready():
    result=evaluate(report(),now=NOW)
    assert result["status"]=="BLOCKED"
    assert "POSTING_TASK_NOT_INSTALLED" in result["problems"]
    assert "SERVER_LOGON_TASK_NOT_INSTALLED" in result["problems"]
    assert "PLAN_EMPTY" in result["warnings"]
    assert result["automatic_posting_authorized_by_this_check"] is False


def test_fresh_report_with_only_old_ticks_is_still_stale_execution():
    ticks=[{"stage":"TICK_START","run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
            "at":"2026-10-31T12:00:00+00:00"},
           {"stage":"TICK_END","run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
            "at":"2026-10-31T12:00:01+00:00","exit_code":0}]
    result=evaluate(report(task=True,logon=True,ticks=ticks),now=NOW)
    assert "NO_RECENT_TICK" in result["warnings"]
    assert "TASK_WITHOUT_RECENT_TICK" in result["problems"]


def test_snapshot_freshness_separate_from_history():
    result=evaluate(report(generated=NOW-timedelta(days=2)),now=NOW)
    assert "SNAPSHOT_STALE" in result["problems"]
    past=evaluate(report(generated=NOW-timedelta(days=2)),now=NOW,historical=True)
    assert "SNAPSHOT_STALE" not in past["problems"]


def test_unmatched_tick_detected_without_exposing_run_details():
    tick=[{"stage":"TICK_START",
           "run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
           "at":NOW.isoformat()}]
    result=evaluate(report(task=True,logon=True,ticks=tick),now=NOW)
    assert "TICK_RUN_INCOMPLETE" in result["warnings"]
    assert "627b4aa2" not in json.dumps(result)


def test_historical_file_validator_is_read_only(tmp_path,capsys):
    path=tmp_path/"archive.json"
    path.write_text(json.dumps(report(generated=NOW-timedelta(days=5))),encoding="utf-8")
    assert main([str(path),"--historical"])==0
    response=json.loads(capsys.readouterr().out)
    assert response["automatic_posting_authorized_by_this_check"] is False


def test_invalid_input_rejected_without_echoing_content(tmp_path,capsys):
    file=tmp_path/"snapshot.json"
    file.write_text('{"secret":"private"}',encoding="utf-8")
    assert main([str(file)])==3
    rendered=capsys.readouterr().out
    assert "private" not in rendered
    assert "READINESS_INPUT_INVALID" in rendered
