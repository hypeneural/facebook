"""Preview must not create or modify the live SQLite DB / daily plan."""
import json
import sys
from datetime import datetime

from app.daily_queue import DailyQueue, TIMEZONE
from scripts import daily_tick


def config(tmp_path):
    media=tmp_path/"approved.jpg"
    media.write_bytes(b"fake-approved-photo")
    return {
        "enabled":False,"allow_unattended":False,
        "timezone":"America/Sao_Paulo","account_id":"principal",
        "rotation_seed":"stable-test-private-seed",
        "slots":["08:00","10:00","16:00","18:00","22:00"],
        "groups_per_slot":1,"max_posts_per_group_per_day":2,
        "allow_repeat_group_per_day":True,
        "groups":[{"url":f"https://www.facebook.com/groups/{100000+i}/","authorized":True}
                  for i in range(4)],
        "creatives":[{"id":"photo","files":[str(media)]}],
        "captions":[{"id":"text","text":"Mensagem aprovada"}],
    }


def test_cli_preview_does_not_create_database(tmp_path,monkeypatch,capsys):
    cfg=tmp_path/"daily.json"
    cfg.write_text(json.dumps(config(tmp_path)),encoding="utf-8")
    target=tmp_path/"production.sqlite"
    monkeypatch.setattr(sys,"argv",["daily_tick.py","--config",str(cfg),"--db",str(target)])
    assert daily_tick.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result["state"]=="PREVIEW_ONLY"
    assert result["jobs"]==5
    assert result["source"]=="ISOLATED_MEMORY"
    assert not target.exists()


def test_cli_preview_keeps_existing_frozen_day_unchanged(tmp_path,monkeypatch,capsys):
    cfgdata=config(tmp_path)
    day=datetime.now(TIMEZONE).date()
    cfg=tmp_path/"daily.json"
    cfg.write_text(json.dumps(cfgdata),encoding="utf-8")
    database=tmp_path/"production.sqlite"
    q=DailyQueue(database)
    q.plan(cfgdata,day)
    original=q.summary()
    q.close()
    monkeypatch.setattr(sys,"argv",["daily_tick.py","--config",str(cfg),"--db",str(database)])
    assert daily_tick.main()==0
    result=json.loads(capsys.readouterr().out)
    assert result["state"]=="PREVIEW_ONLY"
    assert result["source"]=="EXISTING_PLAN"
    q2=DailyQueue(database)
    assert q2.summary()==original
    q2.close()


def test_cli_preview_detects_drift_without_modifying_old_plan(tmp_path,monkeypatch,capsys):
    cfgdata=config(tmp_path)
    old=dict(cfgdata)
    old["slots"]=["11:25"]
    old["groups"]=cfgdata["groups"][:1]
    day=datetime.now(TIMEZONE).date()
    database=tmp_path/"production.sqlite"
    q=DailyQueue(database)
    q.plan(old,day)
    original=q.summary()
    q.close()
    cfg=tmp_path/"daily.json"
    cfg.write_text(json.dumps(cfgdata),encoding="utf-8")
    monkeypatch.setattr(sys,"argv",["daily_tick.py","--config",str(cfg),"--db",str(database)])
    assert daily_tick.main()==3
    result=json.loads(capsys.readouterr().out)
    assert result["state"]=="PLAN_CONFIG_DRIFT"
    q2=DailyQueue(database)
    assert q2.summary()==original
    q2.close()
