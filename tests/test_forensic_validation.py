import copy
import pytest
from app.forensic_report import summarize
from scripts.validate_forensic_report import validate_report

def sample():
    return summarize(
      [{"id":"b8a9a960b1aa21a855ab94c1dd870d26","status":"NEEDS_REVIEW",
        "day":"2026-10-30","slot":"08:00","group_id":"123456",
        "operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa"}],
      [{"job_id":"b8a9a960b1aa21a855ab94c1dd870d26",
        "at":"2026-10-30T11:01:00+00:00","event":"PREFLIGHT_FAILED",
        "code":"SERVER_NOT_READY"}],
      [{"operation_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
        "stage":"REQUEST_ACCEPTED","job_id":"b8a9a960b1aa21a855ab94c1dd870d26",
        "error_code":"TIMEOUT_AT_PUBLISH","source_file":"browser.py",
        "source_line":237}],
      {"schema":"facebook.win11.v1",
       "task":{"exists":True,"state":"Ready","last_result_code":"2147943726"},
       "recent_events":[{"event_id":102,"at_utc":"2026-10-30T11:05:00+00:00"}]},
      [{"run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
       "stage":"TICK_END","exit_code":3}])

def test_generated_report_passes_strict_schema():
    assert validate_report(sample()) is True

def test_rejects_raw_cookie_and_caption_even_if_attacker_edits_json():
    base=sample()
    x=copy.deepcopy(base)
    x["jobs"][0]["caption"]="Cliente privado"
    with pytest.raises(ValueError):
        validate_report(x)
    x=copy.deepcopy(base)
    x["operations"][0]["error_code"]="password=PRIVATE"
    with pytest.raises(ValueError):
        validate_report(x)

def test_rejects_forged_codes_and_urls():
    x=sample()
    x["operations"][0]["error_code"]="SECRET_CUSTOMER_NAME"
    with pytest.raises(ValueError):
        validate_report(x)
    x=sample()
    x["operations"][0]["source_file"]="https://evil.example.com"
    with pytest.raises(ValueError):
        validate_report(x)
