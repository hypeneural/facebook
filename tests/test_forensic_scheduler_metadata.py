"""Regressão: snapshots volumosos e diagnóstico Windows 11 seguro."""
from datetime import datetime, timezone
import pytest
from app.forensic_report import summarize
from scripts.validate_forensic_report import validate_report


def test_large_tick_history_accepted_and_bounded():
    uid="627b4aa2-efa7-42e6-916a-24a408ce00aa"
    ticks=[{"run_id":uid,"stage":"TICK_END","at":"2026-10-30T12:00:00+00:00",
            "exit_code":0,"duration_ms":i} for i in range(2800)]
    report=summarize([],[],[],raw_ticks=ticks)
    assert len(report["ticks"])==2800
    assert validate_report(report) is True


def test_windows_metadata_safe_and_validated():
    raw={"schema":"facebook.win11.v1",
         "event_scan_count":300,"event_scan_truncated":True,
         "task":{"exists":True,"state":"Ready","last_result_code":"0",
                 "last_run_utc":"2026-10-30T11:00:00+00:00",
                 "next_run_utc":"2026-10-30T15:00:00+00:00",
                 "missed_runs":2,"multiple_instances":"IgnoreNew",
                 "logon_type":"Interactive","execution_limit_minutes":30}}
    report=summarize([],[],[],windows=raw)
    assert report["windows"]["missed_runs"]==2
    assert report["windows"]["event_scan_truncated"] is True
    assert validate_report(report) is True
    report["windows"]["logon_type"]="cookie=secret"
    with pytest.raises(ValueError,match="INVALID_WINDOWS_LOGON_TYPE"):
        validate_report(report)


def test_windows_bad_values_sanitized():
    raw={"schema":"facebook.win11.v1",
         "task":{"exists":True,"state":"Ready","last_result_code":"0",
                 "logon_type":"password=private",
                 "multiple_instances":"https://example.invalid/token",
                 "missed_runs":"private string"}}
    out=summarize([],[],[],windows=raw)
    assert out["windows"]["logon_type"]=="Unknown"
    assert out["windows"]["multiple_instances"]=="Unknown"
    assert out["windows"]["missed_runs"] is None
    assert validate_report(out) is True
