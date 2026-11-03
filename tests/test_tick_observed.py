import json
from pathlib import Path
from scripts import tick_observed

def test_tick_wrapper_does_not_log_secrets(tmp_path,monkeypatch):
    monkeypatch.setattr(tick_observed,"ROOT",tmp_path)
    monkeypatch.setattr(tick_observed.daily_tick,"main",lambda:3)
    assert tick_observed.main()==3
    log=(tmp_path/"data"/"diagnostics"/"ticks.jsonl").read_text()
    rows=[json.loads(s) for s in log.splitlines()]
    assert [r["stage"] for r in rows]==["TICK_START","TICK_END"]
    assert rows[1]["exit_code"]==3
    assert "token" not in log and "password" not in log

def test_tick_unhandled_exception_records_only_class(tmp_path,monkeypatch):
    monkeypatch.setattr(tick_observed,"ROOT",tmp_path)
    def broken():
        raise ValueError("cookie=PRIVATE user home C:\\Personal")
    monkeypatch.setattr(tick_observed.daily_tick,"main",broken)
    import pytest
    with pytest.raises(ValueError):
        tick_observed.main()
    log=(tmp_path/"data"/"diagnostics"/"ticks.jsonl").read_text()
    assert "cookie=" not in log and "PRIVATE" not in log and "Personal" not in log
    assert "ValueError" in log
