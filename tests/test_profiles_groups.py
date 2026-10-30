"""Testes locais de grupos/perfis, sem navegador real, fotos ou Facebook."""
from fastapi.testclient import TestClient
from app import main

def test_profile_and_group_registry_without_facebook(monkeypatch,tmp_path):
    monkeypatch.setattr(main,"DATA",tmp_path)
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as client:
        accounts=client.get("/api/accounts").json()
        assert accounts["active"]=="principal"
        assert len(accounts["accounts"])==1
        added=client.post("/api/accounts",json={"name":"Conta 2"})
        assert added.status_code==200
        second=added.json()["created"]["id"]
        assert second!="principal"
        assert len(client.get("/api/accounts").json()["accounts"])==2
        groups=client.post("/api/groups/saved",json={"name":"Grupo teste","group_url":"https://www.facebook.com/groups/123456/"})
        assert groups.status_code==200
        assert groups.json()[0]["url"]=="https://www.facebook.com/groups/123456/"
        duplicated=client.post("/api/groups/saved",json={"name":"Outro nome","group_url":"https://www.facebook.com/groups/123456/"})
        assert len(duplicated.json())==1
        invalid=client.post("/api/groups/saved",json={"name":"Grupo inválido","group_url":"https://example.com/groups/1/"})
        assert invalid.status_code==422

def test_multi_media_preflight_offline():
    from app.validation import validate
    url="https://www.facebook.com/groups/123456/"
    assert validate(url,"legenda",[f"{i}.jpg" for i in range(10)])==url
    from pytest import raises
    with raises(ValueError):
        validate(url,"legenda",[f"{i}.jpg" for i in range(11)])
