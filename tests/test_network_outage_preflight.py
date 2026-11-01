"""Pre-claim connectivity failures are retry-safe, post-claim failures are not."""
from datetime import datetime, timezone

import pytest
from app.daily_queue import DailyQueue
from scripts import daily_tick


def config(tmp_path):
    media=tmp_path/"approved.jpg"
    media.write_bytes(b"test-photo-bytes")
    return {
        "enabled": True, "allow_unattended": True, "timezone": "America/Sao_Paulo",
        "account_id": "principal", "rotation_seed": "stable-private-audit-seed",
        "slots": ["08:00"], "groups_per_slot": 1,
        "groups": [{"url":"https://www.facebook.com/groups/123456789/", "authorized":True}],
        "creatives":[{"id":"photo","files":[str(media)]}],
        "captions":[{"id":"approved","text":"Texto autorizado para teste"}],
    }


def test_tls_transport_failure_is_classified_without_credentials(monkeypatch):
    def offline(*args,**kwargs):
        raise OSError("network down")
    monkeypatch.setattr(daily_tick.socket, "create_connection", offline)
    assert daily_tick.probe_facebook_tls(timeout=0.1) is False


def test_preflight_offline_defers_before_claim(tmp_path, monkeypatch):
    cfg=config(tmp_path)
    states={
        "/health":{"ok":True,"busy":False,"build_revision":"a1b2c3d4e5f6"},
        "/api/accounts":{"active":"principal"},
        "/api/session":{"logged_in":True},
        "/api/post-state":{"state":"NO_OPERATION"},
    }
    monkeypatch.setattr(daily_tick,"fetch_state",lambda path:states[path])
    monkeypatch.setattr(daily_tick,"checkout_revision",lambda:"a1b2c3d4e5f6")
    def offline(account):
        return daily_tick.preflight(account,connectivity_probe=lambda:False)
    calls=[]
    q=DailyQueue(tmp_path/"queue.sqlite")
    try:
        now=datetime(2026,10,31,11,1,tzinfo=timezone.utc)
        result=daily_tick.tick(cfg,q,now=now,execute=True,state_fetch=offline,
                               transport=lambda *args:calls.append(1))
        assert result["state"]=="WAITING_PREFLIGHT"
        assert result["error_code"]=="NETWORK_NOT_READY"
        row=q.summary()[0]
        assert row["status"]=="PLANNED"
        assert q.events(row["id"])[-1]["code"]=="NETWORK_NOT_READY"
        assert calls==[]
    finally:q.close()


def test_after_claim_network_error_is_uncertain_and_never_retried(tmp_path):
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"queue.sqlite")
    calls=[]
    try:
        now=datetime(2026,10,31,11,1,tzinfo=timezone.utc)
        def broken(*args):
            calls.append(1)
            raise ConnectionResetError("connection lost after possible submit")
        first=daily_tick.tick(cfg,q,now=now,execute=True,
                              state_fetch=lambda _:None,transport=broken)
        second=daily_tick.tick(cfg,q,now=now,execute=True,
                               state_fetch=lambda _:None,transport=broken)
        assert first["state"]=="NEEDS_REVIEW"
        assert second["state"]=="PAUSED_FOR_REVIEW"
        assert calls==[1]
    finally:q.close()


def test_uncertain_dispatch_logs_exception_type_but_not_message(tmp_path, monkeypatch):
    import json
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"jobs.sqlite")
    try:
        now=datetime(2026,10,31,11,1,tzinfo=timezone.utc)
        def broken(*args):
            raise ConnectionResetError("PRIVATE COOKIE=secret local-path C:\\Users\\Person")
        result=daily_tick.tick(cfg,q,now=now,execute=True,
                               state_fetch=lambda _:None,transport=broken)
        assert result["state"]=="NEEDS_REVIEW"
        assert result["error_class"]=="ConnectionResetError"
        monkeypatch.setattr(daily_tick,"ROOT",tmp_path)
        monkeypatch.setenv("EVYD_FORENSIC_RUN_ID","627b4aa2-efa7-42e6-916a-24a408ce00aa")
        daily_tick.audit_tick_result(result)
        data=(tmp_path/"data"/"diagnostics"/"ticks.jsonl").read_text()
        assert "ConnectionResetError" in data
        assert "secret" not in data and "C:\\Users" not in data
        assert json.loads(data)["stage"]=="TICK_RESULT"
    finally:q.close()
