"""Testes API locais; NUNCA acessam Facebook ou abrem o navegador."""
from fastapi.testclient import TestClient
from app.main import app

def test_health_and_local_session():
    with TestClient(app,base_url="http://127.0.0.1:8108") as c:
        assert c.get("/health").json()=={"ok":True,"real_facebook_publish_verified":False}
        assert c.get("/api/session").json()["logged_in"] is False

def test_invalid_publish_rejected_without_network():
    with TestClient(app,base_url="http://127.0.0.1:8108") as c:
        r=c.post("/api/publish",data={"group_url":"https://www.facebook.com/groups/123","caption":""})
        assert r.status_code==422

def test_cross_site_mutation_blocked():
    with TestClient(app,base_url="http://127.0.0.1:8108") as c:
        r=c.post("/api/browser/open",headers={"Origin":"https://evil.example","Sec-Fetch-Site":"cross-site"})
        assert r.status_code==403

def test_host_blocked():
    with TestClient(app,base_url="http://evil.example") as c:
        assert c.get("/health").status_code==403
