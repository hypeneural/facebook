"""Forensic regression: never silently post from stale daily plan."""
from collections import Counter
from datetime import datetime,timezone
import json
import sqlite3
from app.daily_queue import DailyQueue,inspect_day_plan
from scripts.daily_tick import tick
from scripts.export_forensics import collect
from scripts.validate_forensic_report import validate_report


def config(groups=4,slots=None):
    return {
        "enabled":False,"allow_unattended":False,
        "timezone":"America/Sao_Paulo","account_id":"principal",
        "rotation_seed":"deterministic-auditable-seed",
        "slots":slots or ["08:00","10:00","16:00","18:00","22:00"],
        "groups_per_slot":1,"max_posts_per_group_per_day":2,
        "allow_repeat_group_per_day":True,
        "groups":[{"url":f"https://www.facebook.com/groups/{1000000+i}/","authorized":True}
                  for i in range(groups)],
        "creatives":[{"id":f"photo-{i}"} for i in range(3)],
        "captions":[{"id":f"text-{i}"} for i in range(2)]
    }


def test_new_plan_five_slots_four_groups_balanced(tmp_path):
    cfg=config()
    queue=DailyQueue(tmp_path/"fresh.sqlite")
    try:
        queue.plan(cfg,"2026-11-03")
        rows=queue.summary()
        diagnosis=inspect_day_plan(cfg,rows,"2026-11-03")
        assert diagnosis["state"]=="PLAN_MATCH"
        assert diagnosis["planned_jobs"]==5 and diagnosis["expected_jobs"]==5
        assert max(Counter(x["group_id"] for x in rows).values())<=2
        assert sorted(Counter(x["creative_id"] for x in rows).values())==[1,2,2]
        assert sorted(Counter(x["caption_id"] for x in rows).values())==[2,3]
        assert queue.plan(cfg,"2026-11-03") and queue.summary()==rows
    finally:
        queue.close()


def test_changed_schedule_causes_read_only_drift_no_rewrite(tmp_path):
    cfg=config(groups=1,slots=["11:25"])
    q=DailyQueue(tmp_path/"historic.sqlite")
    try:
        q.plan(cfg,"2026-11-03")
        original=q.summary()
        updated=config()
        diagnosis=inspect_day_plan(updated,original,"2026-11-03")
        assert diagnosis["state"]=="PLAN_CONFIG_DRIFT"
        assert "PLAN_SLOT_MISMATCH" in diagnosis["codes"]
        assert "PLAN_COUNT_MISMATCH" in diagnosis["codes"]
        result=tick(updated,q,now=datetime(2026,11,3,14,30,tzinfo=timezone.utc),execute=False)
        assert result["state"]=="PLAN_CONFIG_DRIFT"
        assert q.summary()==original
        assert not any(x["status"]=="NEEDS_REVIEW" for x in q.summary())
    finally:q.close()


def test_diagnostics_export_includes_nested_windows_failure(tmp_path):
    path=tmp_path/"daily.json"
    path.write_text(json.dumps(config()),encoding="utf8")
    diag=tmp_path/"diagnostics"
    diag.mkdir()
    (diag/"windows.json").write_text(json.dumps({
        "schema":"facebook.win11.v1",
        "task":{"exists":False,"state":"Unknown","last_result_code":None},
        "errors":["EVENT_LOG_Exception"],"recent_event_ids":[],
        "recent_events":[]}),encoding="utf8")
    report=collect(tmp_path)
    assert report["windows"]["collection_errors"]==["EVENT_LOG_Exception"]
    assert "EVENT_LOG_Exception" in report["collection_errors"]
    assert report["plan"]["state"]=="PLAN_EMPTY"
    assert validate_report(report) is True


def test_stale_plan_exposed_in_public_safe_snapshot(tmp_path):
    cfg=config(groups=1,slots=["11:25"])
    q=DailyQueue(tmp_path/"daily-queue.sqlite")
    try:q.plan(cfg,"2026-11-03")
    finally:q.close()
    changed=config()
    (tmp_path/"daily.json").write_text(json.dumps(changed),encoding="utf8")
    # Cross-platform and independent of real current date: function directly.
    with sqlite3.connect(tmp_path/"daily-queue.sqlite") as db:
        db.row_factory=sqlite3.Row
        rows=[dict(x) for x in db.execute("SELECT * FROM jobs_v2")]
    assert inspect_day_plan(changed,rows,"2026-11-03")["state"]=="PLAN_CONFIG_DRIFT"
