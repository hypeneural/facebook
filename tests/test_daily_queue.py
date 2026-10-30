from datetime import datetime,timezone,timedelta
import sqlite3
import pytest
from app.daily_queue import DailyQueue,validate_config

@pytest.fixture
def config():
    return {
        "enabled":False,"timezone":"America/Sao_Paulo","account_id":"principal",
        "rotation_seed":"stable-private-seed-for-audit",
        "slots":["08:00","10:00","16:00","18:00","22:00"],
        "groups_per_slot":1,
        "groups":[{"url":f"https://www.facebook.com/groups/{100000+i}/","authorized":True} for i in range(5)],
        "creatives":[{"id":"photo1"},{"id":"video2"}],
        "captions":[{"id":"caption1"},{"id":"caption2"}]
    }

def test_stable_replanning_is_idempotent(tmp_path,config):
    q=DailyQueue(tmp_path/"jobs.db")
    try:
        assert len(q.plan(config,"2026-10-31"))==5
        first=q.summary()
        q.plan(config,"2026-10-31")
        assert q.summary()==first
        assert len({x["group_id"] for x in first})==5
        assert len({x["creative_id"] for x in first})>=1
    finally:q.close()

def test_unauthorized_destination_never_planned(tmp_path,config):
    config["groups"][0]["authorized"]=False
    with pytest.raises(ValueError,match="authorized"):
        DailyQueue(tmp_path/"x.db").plan(config,"2026-10-31")

def test_claim_is_transactional_and_crash_stops_queue(tmp_path,config):
    p=tmp_path/"jobs.db"
    q=DailyQueue(p)
    try:
        q.plan(config,"2026-10-31")
        now=datetime(2026,10,31,13,3,tzinfo=timezone.utc) # 10:03 Sao Paulo
        first=q.claim_one(now=now)
        assert first is not None
        assert q.claim_one(now=now) is None
        q.close()
        q=DailyQueue(p)
        assert q.claim_one(now=now) is None
        q.annotate(first["id"],"uuid-example","SUBMITTED_UNVERIFIED")
        assert q.events(first["id"])[-1]["event"]=="DISPATCH_RESULT"
        q.resolve(first["id"],"SKIPPED","Operador revisou o destino e dispensou reenvio.")
        assert q.claim_one(now=now) is not None
    finally:q.close()

def test_missed_windows_are_skipped(tmp_path,config):
    q=DailyQueue(tmp_path/"jobs.db")
    try:
        q.plan(config,"2026-10-31")
        far=datetime(2026,11,1,16,0,tzinfo=timezone.utc)
        assert q.claim_one(now=far) is None
        assert all(x["status"]=="MISSED" for x in q.summary())
    finally:q.close()

def test_cannot_auto_reset_to_pending(tmp_path,config):
    q=DailyQueue(tmp_path/"jobs.db")
    try:
        q.plan(config,"2026-10-31")
        item=q.claim_one(datetime(2026,10,31,13,3,tzinfo=timezone.utc))
        with pytest.raises(ValueError):
            q.resolve(item["id"],"PLANNED","Quero reenviar automaticamente")
    finally:q.close()

def test_invalid_times_and_duplicate_groups_fail_closed(config):
    config["slots"]=["08:00","08:00"]
    with pytest.raises(ValueError,match="Horários"):
        validate_config(config)
    config["slots"]=["08:00"]
    config["groups"].append(config["groups"][0])
    with pytest.raises(ValueError,match="duplicado"):
        validate_config(config)

def test_plan_timezone_uses_brasilia_and_day_boundaries(tmp_path,config):
    q=DailyQueue(tmp_path/"jobs.db")
    try:
        q.plan(config,"2026-10-31")
        first=q.summary()
        slot8=next(x for x in first if x["slot"]=="08:00")
        assert slot8["due_utc"].startswith("2026-10-31T11:00:00")
    finally:q.close()
