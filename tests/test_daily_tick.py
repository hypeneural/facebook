from datetime import datetime,timezone
from scripts.daily_tick import tick,select_content
from app.daily_queue import DailyQueue

def config(tmp_path):
    photo=tmp_path/"x.jpg"
    photo.write_bytes(b"test-file")
    return {
       "enabled":True,"allow_unattended":True,"timezone":"America/Sao_Paulo",
       "account_id":"principal","rotation_seed":"stable-seed-only-for-tests",
       "slots":["08:00"],"groups_per_slot":1,
       "groups":[{"url":"https://www.facebook.com/groups/123456/","authorized":True}],
       "creatives":[{"id":"one","files":[str(photo)]}],
       "captions":[{"id":"a","text":"Texto aprovado"}]
    }

def test_default_dry_run_does_not_contact_facebook(tmp_path):
    cfg=config(tmp_path)
    db=DailyQueue(tmp_path/"a.sqlite")
    try:
        output=tick(cfg,db,now=datetime(2026,10,31,11,1,tzinfo=timezone.utc),
                    execute=False,state_fetch=lambda _: 1/0)
        assert output["state"]=="PREVIEW_ONLY"
        assert len(db.summary())==1
    finally:db.close()

def test_auto_disabled_by_default(tmp_path):
    cfg=config(tmp_path)
    cfg["enabled"]=False
    db=DailyQueue(tmp_path/"a.sqlite")
    try:
        assert tick(cfg,db,now=datetime(2026,10,31,11,1,tzinfo=timezone.utc),
                    execute=True)["state"]=="DISABLED"
    finally:db.close()

def test_once_only_and_needs_review_even_if_transport_fails(tmp_path):
    cfg=config(tmp_path)
    db=DailyQueue(tmp_path/"a.sqlite")
    now=datetime(2026,10,31,11,1,tzinfo=timezone.utc)
    calls=[]
    def send(u,c,paths):
        calls.append(1)
        raise TimeoutError("simulated crash after possible upload")
    try:
        first=tick(cfg,db,now=now,execute=True,transport=send,state_fetch=lambda _:None)
        assert first["state"]=="NEEDS_REVIEW"
        second=tick(cfg,db,now=now,execute=True,transport=send,state_fetch=lambda _:None)
        assert second["state"]=="PAUSED_FOR_REVIEW"
        assert calls==[1]
    finally:db.close()

def test_content_changed_after_planning_blocks_dispatch(tmp_path):
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"test.sqlite")
    try:
        q.plan(cfg,"2026-10-31")
        cfg["captions"][0]["text"]="Texto diferente!"
        job=q.summary()[0]
        try:
            select_content(job,cfg)
            raise AssertionError("Changed content was silently used")
        except ValueError as exc:
            assert str(exc)=="CONFIG_OR_MEDIA_CHANGED"
    finally:q.close()

def test_preflight_error_is_audited_without_claim(tmp_path):
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"test.sqlite")
    try:
        output=tick(cfg,q,now=datetime(2026,10,31,11,1,tzinfo=timezone.utc),
                    execute=True,state_fetch=lambda x: (_ for _ in ()).throw(RuntimeError("ACCOUNT_NOT_READY")))
        assert output["state"]=="WAITING_PREFLIGHT"
        job=q.summary()[0]
        assert job["status"]=="PLANNED"
        assert q.events(job["id"])[-1]["code"]=="ACCOUNT_NOT_READY"
    finally:q.close()

def test_dispatch_checks_matching_account_before_claim(tmp_path):
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"test.sqlite")
    try:
        def fail(account):
            raise RuntimeError("ACCOUNT_NOT_READY")
        result=tick(cfg,q,now=datetime(2026,10,31,11,1,tzinfo=timezone.utc),
                    execute=True,state_fetch=fail)
        assert result["state"]=="WAITING_PREFLIGHT"
        assert q.summary()[0]["status"]=="PLANNED"
    finally:q.close()

def test_media_bytes_changed_same_path_prevents_post(tmp_path):
    cfg=config(tmp_path)
    q=DailyQueue(tmp_path/"asset.sqlite")
    try:
        q.plan(cfg,"2026-10-31")
        job=q.summary()[0]
        media=tmp_path/"x.jpg"
        media.write_bytes(b"DIFFERENT_FILE_SAME_PATH")
        try:
            select_content(job,cfg)
            raise AssertionError("Changed file bytes not detected")
        except ValueError as exc:
            assert str(exc)=="CONFIG_OR_MEDIA_CHANGED"
    finally:q.close()
