"""Forensic readiness gate: evaluate published snapshots without mistaking freshness for activity.

Read-only. Emits only stable codes and counts, never cookies, media paths or raw JSON.
Use --historical in CI for archived snapshots; --operational locally after a reboot.
A sanitized snapshot cannot prove Facebook posting or authenticated browser state.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts.validate_forensic_report import validate_report


def utc(value):
    if not isinstance(value,str):
        return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def evaluate(report, *, now=None, max_age_hours=6, historical=False):
    """Returns a closed-code diagnostic; never classifies a published post as verified."""
    validate_report(report)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    problems=set()
    warnings=set()
    win=report.get("windows",{})
    plan=report.get("plan",{})
    ticks=report.get("ticks",[])
    logons=report.get("server_runs",[])
    generated=utc(report.get("generated_at"))
    if generated is None:
        problems.add("SNAPSHOT_TIME_INVALID")
    elif not historical and generated>now+timedelta(minutes=5):
        problems.add("SNAPSHOT_FROM_FUTURE")
    elif not historical and now-generated>timedelta(hours=max_age_hours):
        problems.add("SNAPSHOT_STALE")

    if report.get("collection_errors"):
        warnings.add("COLLECTION_PARTIAL")
    if win.get("collection_errors"):
        warnings.add("WINDOWS_COLLECTION_PARTIAL")
    if win.get("event_log_status") in {"DISABLED","ERROR","UNKNOWN"}:
        warnings.add("EVENT_LOG_UNAVAILABLE")
    if not win:
        warnings.add("WINDOWS_TELEMETRY_ABSENT")
    if plan.get("state")=="PLAN_CONFIG_DRIFT":
        problems.add("PLAN_CONFIG_DRIFT")
    elif plan.get("state") in {"CONFIG_MISSING","CONFIG_INVALID"}:
        problems.add("PLAN_CONFIG_INVALID")
    elif plan.get("state")=="PLAN_EMPTY":
        warnings.add("PLAN_EMPTY")
    elif not plan:
        warnings.add("PLAN_TELEMETRY_ABSENT")

    if not win.get("task_exists"):
        problems.add("POSTING_TASK_NOT_INSTALLED")
    if not win.get("server_logon_task_exists"):
        problems.add("SERVER_LOGON_TASK_NOT_INSTALLED")
    if not win.get("forensic_sync_task_exists"):
        warnings.add("FORENSIC_SYNC_NOT_INSTALLED")
    if win.get("task_exists"):
        if win.get("multiple_instances")!="IgnoreNew":
            problems.add("UNSAFE_TASK_CONCURRENCY")
        if win.get("logon_type")!="Interactive":
            problems.add("UNSAFE_TASK_LOGON_TYPE")

    if not historical:
        good_times=[x for x in (utc(t.get("at")) for t in ticks) if x is not None]
        latest_tick=max(good_times,default=None)
        if not latest_tick or now-latest_tick>timedelta(hours=24):
            warnings.add("NO_RECENT_TICK")
        if win.get("task_exists") and (
            latest_tick is None or now-latest_tick>timedelta(hours=24)):
            problems.add("TASK_WITHOUT_RECENT_TICK")
        # An unmatched START is meaningful only if the most recent event isn't
        # simply a truncated history boundary; check each run whose start is present.
        by_run={}
        for record in ticks:
            run=record.get("run_id")
            if run:
                by_run.setdefault(run,set()).add(record.get("stage"))
        for stages in by_run.values():
            if "TICK_START" in stages and not ("TICK_END" in stages or "TICK_EXCEPTION" in stages):
                warnings.add("TICK_RUN_INCOMPLETE")
                break

        # A fresh exported report may still contain only OLD startup events.
        good_logons=[x for x in (utc(t.get("at")) for t in logons) if x is not None]
        if not good_logons or now-max(good_logons)>timedelta(hours=48):
            warnings.add("NO_RECENT_SERVER_LOGON_EVENT")

    if report.get("totals",{}).get("job_statuses",{}).get("NEEDS_REVIEW",0):
        problems.add("PENDING_PUBLICATION_REVIEW")

    return {
        "schema":"facebook.readiness.v1",
        "status":"BLOCKED" if problems else ("PARTIAL" if warnings else "DIAGNOSTICS_OK"),
        "problems":sorted(problems),
        "warnings":sorted(warnings),
        "statistics":{"ticks":len(ticks),"server_runs":len(logons),
                      "jobs":report.get("totals",{}).get("jobs",0)},
        "post_publication_verified_by_this_check":False,
        "automatic_posting_authorized_by_this_check":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("snapshot",type=Path)
    p.add_argument("--historical",action="store_true")
    p.add_argument("--max-age-hours",type=int,default=6)
    args=p.parse_args(argv)
    if not 1<=args.max_age_hours<=168:
        print(json.dumps({"schema":"facebook.readiness.v1",
                          "status":"BLOCKED","problems":["INVALID_MAX_AGE"]}))
        return 2
    try:
        if args.snapshot.stat().st_size>4*1024*1024:
            raise ValueError("TOO_LARGE")
        report=json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        result=evaluate(report,historical=args.historical,max_age_hours=args.max_age_hours)
    except (OSError,ValueError,TypeError):
        result={"schema":"facebook.readiness.v1",
                "status":"BLOCKED","problems":["READINESS_INPUT_INVALID"],
                "automatic_posting_authorized_by_this_check":False}
    print(json.dumps(result,sort_keys=True))
    # Historical mode is an analytics check, not a CI gate requiring tasks installed.
    if args.historical:return 0 if result.get("status")!="BLOCKED" or result.get("problems")!=["READINESS_INPUT_INVALID"] else 2
    return 0 if result.get("status")=="DIAGNOSTICS_OK" else 3


if __name__=="__main__":
    raise SystemExit(main())
