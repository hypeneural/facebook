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

def test_operation_correlation_and_uncertain_result(monkeypatch,tmp_path):
    from app import main
    monkeypatch.setattr(main,"DATA",tmp_path)
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as c:
        async def fake_run(name,*args):
            if name=="publish":
                operation_id=args[-1]
                main.browser.audit.mark_submit_intent(operation_id)
                raise RuntimeError("simulated browser failure after durable intent")
            if name=="accounts":
                return {"active":"principal"}
            return {"logged_in":False}
        monkeypatch.setattr(main.browser,"run",fake_run)
        r=c.post("/api/publish",data={"group_url":"https://www.facebook.com/groups/123456","caption":"Teste sem enviar"})
        assert r.status_code==200
        output=r.json()
        assert output["status"]=="SUBMITTED_UNVERIFIED"
        assert output["operation_id"]
        trace=c.get("/api/operations").json()
        assert trace[0]["operation_id"]==output["operation_id"]
        assert trace[0]["next_action"]=="VERIFICAR_NO_GRUPO_SEM_REENVIAR"
        assert all("caption" not in event for event in trace[0]["events"])


def test_file_rejection_has_operation_id(monkeypatch,tmp_path):
    from app import main
    monkeypatch.setattr(main,"DATA",tmp_path)
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as c:
        r=c.post("/api/publish",data={"group_url":"https://www.facebook.com/groups/123456","caption":"ok"},files={"media":("empty.jpg",b"","image/jpeg")})
        assert r.status_code==422
        assert "Operação" in r.json()["detail"]
        operations=c.get("/api/operations").json()
        assert operations[0]["stage"]=="UPLOAD_REJECTED"
        assert operations[0]["error_code"]=="UPLOAD_INVALID"
