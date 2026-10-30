"""Simulação offline do watchdog: nunca envia postagem nem acessa Facebook."""
import json
import shutil
import subprocess
import pytest
from app.browser import Browser
from app.post_state import classify_post_ui, requires_hold, POST_UI_JS

def test_hold_is_conservative():
    for x in ("POSTING_IN_PROGRESS","POSTING_STILL_VISIBLE","DIALOG_OPEN_UNVERIFIED",
              "OBSERVATION_UNAVAILABLE","FACEBOOK_WARNING","BROWSER_UNAVAILABLE"):
        assert requires_hold(x)
    assert not requires_hold("POST_UI_CLOSED_UNVERIFIED")
    assert not requires_hold("PENDING_REVIEW")

def test_previous_post_blocks_navigation_and_new_publish(tmp_path):
    bot=Browser(tmp_path/"chrome-profile")
    bot.last_submission={"operation_id":"123","account_id":"principal","media_kind":"video"}
    bot._post_state=lambda: {"state":"POSTING_IN_PROGRESS","operation_id":"123"}
    with pytest.raises(ValueError,match="PREVIOUS_POST_STILL_ACTIVE"):
        bot._group("https://www.facebook.com/groups/123456/")
    with pytest.raises(ValueError,match="PREVIOUS_POST_STILL_ACTIVE"):
        bot._publish("https://www.facebook.com/groups/123456/","nova legenda",[],None)
    with pytest.raises(ValueError,match="PREVIOUS_POST_STILL_ACTIVE"):
        bot._select_account("principal")
    bot.pool.shutdown(wait=False)

def test_post_monitor_exits_on_video_processing(tmp_path):
    bot=Browser(tmp_path/"chrome-profile")
    states=iter(["POSTING_IN_PROGRESS","VIDEO_PROCESSING"])
    bot._post_state=lambda: {"state":next(states)}
    events=[]
    bot._emit=lambda op,stage,**kw: events.append((stage,kw.get("post_ui_state")))
    bot.page=type("Page",(),{"wait_for_timeout":lambda self,x:None})()
    assert bot._monitor_post_submit("op","video",0)=="VIDEO_PROCESSING"
    assert ("POST_UI_OBSERVED","POSTING_IN_PROGRESS") in events
    assert ("POST_UI_OBSERVED","VIDEO_PROCESSING") in events
    bot.pool.shutdown(wait=False)

@pytest.mark.skipif(shutil.which("node") is None,reason="Node não instalado")
@pytest.mark.parametrize("dialog,leaf,banner,expected",[
    (True,"Postando","", "POSTING_IN_PROGRESS"),
    (True,"Posting...","", "POSTING_IN_PROGRESS"),
    (False,"","Processando vídeo", "VIDEO_PROCESSING"),
    (True,"Aguardando aprovação","", "PENDING_REVIEW"),
    (False,"","", "POST_UI_CLOSED_UNVERIFIED"),
])
def test_post_ui_js_in_dom_fixture(dialog,leaf,banner,expected):
    js=r"""
const code=process.argv[1], d=process.argv[2]==="1", t=process.argv[3], b=process.argv[4];
const leaf = str => ({
 textContent:str,children:[],getBoundingClientRect(){return {width:100,height:20}}
});
const root = str => ({
 textContent:str,children:[leaf(str)],
 getBoundingClientRect(){return {width:400,height:500}},
 querySelectorAll(){return [leaf(str)];}
});
global.getComputedStyle=()=>({visibility:"visible",display:"block"});
global.document={querySelectorAll(query){
 if(query==='[role="dialog"]')return d?[root(t)]:[];
 if(query==='[role="status"],[role="alert"]')return b?[root(b)]:[];
 return [];
}};
console.log(JSON.stringify(eval('('+code+')')()));
"""
    x=subprocess.run(["node","-e",js,POST_UI_JS,"1" if dialog else "0",leaf,banner],
                     capture_output=True,text=True,timeout=10,check=True)
    assert classify_post_ui(json.loads(x.stdout))==expected

def test_post_status_endpoint_without_navigating(monkeypatch):
    from app import main
    from fastapi.testclient import TestClient
    with TestClient(main.app,base_url="http://127.0.0.1:8108") as client:
        async def inspect(name,*args):
            assert name=="inspect_post_state"
            return {"state":"POSTING_IN_PROGRESS","operation_id":"op-test"}
        monkeypatch.setattr(main.browser,"run",inspect)
        data=client.get("/api/post-state").json()
        assert data["state"]=="POSTING_IN_PROGRESS"
        assert data["operation_id"]=="op-test"
