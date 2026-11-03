"""Windows PowerShell UTF-8 BOM must not hide the first startup event."""
import json
from uuid import uuid4
from scripts.export_forensics import read_jsonl,collect
from scripts.validate_forensic_report import validate_report


def test_legacy_windows_bom_first_jsonl_row(tmp_path):
    uid=str(uuid4())
    path=tmp_path/"server-logon.jsonl"
    entries=[
        {"run_id":uid,"stage":"SERVER_LOGON_START","at":"2026-10-31T17:00:00+00:00"},
        {"run_id":uid,"stage":"SERVER_LOGON_END","at":"2026-10-31T17:00:01+00:00"},
    ]
    path.write_bytes(b"\xef\xbb\xbf"+b"\n".join(json.dumps(e).encode() for e in entries)+b"\n")
    assert [r["stage"] for r in read_jsonl(path)]==["SERVER_LOGON_START","SERVER_LOGON_END"]


def test_export_keeps_complete_legacy_windows_startup_pair(tmp_path):
    uid=str(uuid4())
    diag=tmp_path/"diagnostics"
    diag.mkdir()
    records=[
        {"run_id":uid,"stage":"SERVER_LOGON_START","at":"2026-10-31T17:00:00+00:00"},
        {"run_id":uid,"stage":"SERVER_LOGON_END","at":"2026-10-31T17:00:01+00:00"}
    ]
    (diag/"server-logon.jsonl").write_bytes(
        b"\xef\xbb\xbf"+b"\n".join(json.dumps(x).encode() for x in records)+b"\n")
    report=collect(tmp_path)
    assert [x["stage"] for x in report["server_runs"]]==[
        "SERVER_LOGON_START","SERVER_LOGON_END"]
    assert validate_report(report) is True
