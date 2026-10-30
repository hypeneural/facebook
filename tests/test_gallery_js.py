"""Smoke da expressão JS de colagem com DOM sintético, sem Playwright/FB."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import pytest

def gallery_source():
    tree=ast.parse((Path(__file__).resolve().parents[1]/"app"/"browser.py").read_text(encoding="utf8"))
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="gallery_script" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("gallery_script ausente")

@pytest.mark.skipif(shutil.which("node") is None,reason="Node.js indisponível no runner")
@pytest.mark.parametrize("badge,expected",[
    ("+2",2),
    ("mais 2",2),
    ("Editar tudo",None),
    ("+1",1),
])
def test_facebook_gallery_badge_js(badge,expected):
    js=gallery_source()
    harness="""
const src=process.argv[1];
const badge=process.argv[2];
const mkimg=(i)=>({
 currentSrc:"blob:image"+i,src:"blob:image"+i,complete:true,naturalWidth:400,
 getBoundingClientRect(){return {width:120,height:120};}
});
const node={
 textContent:badge,children:[],
 getBoundingClientRect(){return {width:60,height:15};}
};
const dialog={
 getBoundingClientRect(){return {width:400,height:500};},
 querySelectorAll(q){return q==="span,div"?[node]:[0,1,2,3].map(mkimg);}
};
global.document={querySelectorAll(){return [dialog];}};
global.getComputedStyle=()=>({visibility:"visible"});
console.log(JSON.stringify(eval("("+src+")")([])));
"""
    run=subprocess.run(["node","-e",harness,js,badge],capture_output=True,text=True,timeout=10,check=True)
    obj=json.loads(run.stdout)
    assert obj["visible"]==4
    assert obj["overflow"]==expected
