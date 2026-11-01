import json
from pathlib import Path
from scripts.validate_report_directory import verify_directory
from app.forensic_report import summarize

def test_directory_without_reports_is_successful(tmp_path):
    assert verify_directory(tmp_path/"reports")==0

def test_directory_rejects_unexpected_fields(tmp_path):
    directory=tmp_path/"reports"
    directory.mkdir()
    report=summarize([],[],[])
    (directory/"2026-10-30.json").write_text(json.dumps(report),encoding="utf8")
    assert verify_directory(directory)==0
    report["jobs"]=[{"job_id":"b8a9a960b1aa21a855ab94c1dd870d26",
                     "status":"PLANNED","cookie":"SECRET"}]
    (directory/"2026-10-30.json").write_text(json.dumps(report),encoding="utf8")
    assert verify_directory(directory)==2
