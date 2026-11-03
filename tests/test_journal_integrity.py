"""Forensic exporter must not silently discard corrupt records or old tail windows."""
import json
from scripts.export_forensics import collect,read_jsonl
from scripts.validate_forensic_report import validate_report


def test_invalid_jsonl_is_exposed_without_raw_content(tmp_path):
    log=tmp_path/"operations.jsonl"
    log.write_text('{"operation_id": "627b4aa2-efa7-42e6-916a-24a408ce00aa", "stage":"SUBMIT_INTENT"}\n'
                   'password=DO_NOT_EXPORT\n',encoding="utf8")
    report=collect(tmp_path)
    assert "OPERATIONS_JOURNAL_INVALID_LINES" in report["collection_errors"]
    assert "DO_NOT_EXPORT" not in json.dumps(report)
    assert validate_report(report) is True


def test_truncated_tail_is_not_mistaken_for_full_history(tmp_path):
    log=tmp_path/"diagnostics"/"ticks.jsonl"
    log.parent.mkdir()
    valid={"run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa",
           "stage":"TICK_END","at":"2026-11-02T12:00:00+00:00"}
    with log.open("w",encoding="utf8") as f:
        for _ in range(20):
            f.write(json.dumps(valid)+"\n")
    stats={}
    assert read_jsonl(log,tail_bytes=100,stats=stats)
    assert stats["truncated"] is True


def test_complete_good_journal_has_no_new_errors(tmp_path):
    root=tmp_path/"diagnostics"
    root.mkdir()
    (root/"ticks.jsonl").write_text(
      '{"run_id":"627b4aa2-efa7-42e6-916a-24a408ce00aa","stage":"TICK_END"}\n')
    report=collect(tmp_path)
    assert not any("JOURNAL" in c for c in report["collection_errors"])
