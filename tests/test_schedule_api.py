from fastapi.testclient import TestClient
from app.daily_queue import DailyQueue
from datetime import datetime,timezone

def test_schedule_read_only_api(monkeypatch,tmp_path):
    from app import main
    work=tmp_path/"Anna Helena"
    work.mkdir()
    monkeypatch.setattr(main,"DATA",work)
    q=DailyQueue(work/"daily-queue.sqlite")
    cfg={
        "enabled":False,"timezone":"America/Sao_Paulo","account_id":"principal",
        "rotation_seed":"stable-seed-for-tests","slots":["08:00"],"groups_per_slot":1,
        "groups":[{"url":"https://www.facebook.com/groups/123456/","authorized":True}],
        "creatives":[{"id":"one"}],"captions":[{"id":"txt"}]
    }
    day=datetime.now(timezone.utc).astimezone(__import__("app.daily_queue",fromlist=["TIMEZONE"]).TIMEZONE).date().isoformat()
    q.plan(cfg,day)
    jid=q.summary()[0]["id"]
    q.close()
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as client:
        r=client.get("/api/schedule")
        assert r.status_code==200
        data=r.json()
        assert data["state"]=="READY"
        assert len(data["jobs"])==1
        assert data["jobs"][0]["id"]==jid
        assert "manifest_sha256" not in data["jobs"][0]
        events=client.get("/api/schedule/events/"+jid)
        assert events.status_code==200
        assert events.json()["job_id"]==jid
        assert client.get("/api/schedule/events/invalid").status_code==422

def test_schedule_get_without_database_is_safe(monkeypatch,tmp_path):
    from app import main
    monkeypatch.setattr(main,"DATA",tmp_path)
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as client:
        r=client.get("/api/schedule")
        assert r.status_code==200
        assert r.json()["state"]=="NOT_CONFIGURED"
