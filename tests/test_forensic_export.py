import json
from pathlib import Path
from app.forensic_report import summarize,sanitize_operation
from scripts.export_forensics import collect

def test_never_export_secrets_or_caption_or_raw_url():
    raw=[{"operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
          "stage":"SUBMIT_RETURNED","group_id":"389335997243726",
          "account_id":"principal","caption":"Familia cliente secret","cookie":"c_user=123",
          "url":"https://example.com/private?token=secret","password":"MY_PASSWORD",
          "error_code":"UNCLASSIFIED_API","duration_ms":1200}]
    report=summarize([],[],raw)
    out=json.dumps(report)
    for forbidden in ("Familia cliente secret","c_user","MY_PASSWORD","389335997243726","principal","example.com","token"):
        assert forbidden not in out
    assert report["operations"][0]["duration_ms"]==1200
    assert report["operations"][0]["stage"]=="SUBMIT_RETURNED"

def test_unknown_stages_codes_are_not_reflected():
    data=sanitize_operation({"operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
            "stage":"https://bad.site/token","error_code":"secret plaintext here",
            "account_id":"abc"})
    assert data is not None
    assert "stage" not in data
    assert data["error_code"]=="UNCLASSIFIED"

def test_job_and_event_sanitization():
    job={"id":"b8a9a960b1aa21a855ab94c1dd870d26","status":"NEEDS_REVIEW",
         "day":"2026-10-30","slot":"08:00","group_id":"555551","caption_id":"hello",
         "caption":"User private content","operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa"}
    data=summarize([job],[{"job_id":job["id"],"at":"2026-10-30T11:00:00+00:00",
          "event":"PREFLIGHT_FAILED","code":"SERVER_NOT_READY","raw_error":"cookie=abc"}],[])
    out=json.dumps(data)
    assert "User private content" not in out and "555551" not in out and "cookie=" not in out
    assert data["totals"]["job_statuses"]["NEEDS_REVIEW"]==1
    assert data["job_events"][0]["code"]=="SERVER_NOT_READY"

def test_collect_empty_data_with_no_db(tmp_path):
    assert collect(tmp_path)["totals"]["jobs"]==0

def test_collect_operations_not_leak_unexpected_fields(tmp_path):
    (tmp_path/"operations.jsonl").write_text(json.dumps({"operation_id":
      "627b4aa2-efa7-42e6-916a-24a408ce00aa","stage":"SUBMITTED_UNVERIFIED",
      "token":"VERY_SECRET"})+"\n",encoding="utf8")
    text=json.dumps(collect(tmp_path))
    assert "VERY_SECRET" not in text

def test_corrupted_sqlite_still_generates_diagnostic_report(tmp_path):
    (tmp_path/"daily-queue.sqlite").write_bytes(b"not an sqlite database")
    report=collect(tmp_path)
    assert "SQLITE_READ_FAILED" in report["collection_errors"]
    assert report["totals"]["jobs"]==0
    assert report["schema"]=="facebook.forensic.v1"

def test_exception_location_exposes_only_source_basename_and_class():
    from app.telemetry import exception_location
    try:
        raise RuntimeError("cookie=secret customer private path")
    except RuntimeError as exc:
        loc=exception_location(exc)
        out=json.dumps(loc)
    assert loc["error_class"]=="RuntimeError"
    assert loc["source_line"]>0
    assert "/" not in loc.get("source_file","")
    assert "secret" not in out and "customer" not in out and "cookie" not in out

def test_windows_events_sanitized_without_raw_messages():
    report=summarize([],[],[],{
       "schema":"facebook.win11.v1",
       "task":{"exists":True,"state":"Ready","last_result_code":"2147943726"},
       "recent_event_ids":[100,102,200],
       "recent_events":[{"event_id":100,"at_utc":"2026-10-30T13:00:00+00:00",
                         "message":"cookie=DO_NOT_EXPORT"}],
       "errors":["EVENT_LOG_CimException"]})
    text=json.dumps(report)
    assert "DO_NOT_EXPORT" not in text
    assert report["windows"]["recent_events"][0]["event_id"]==100
    assert report["windows"]["collection_errors"]==["EVENT_LOG_CimException"]
