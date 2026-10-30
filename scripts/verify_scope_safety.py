"""Forensic preflight: FAIL when health/revision/dialog cannot be verified.

--offline runs test/scope checks only, without requiring the Windows desktop.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT_DIR=Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0,str(ROOT_DIR))

def check_editor_scope_constant():
    from app.browser import EDITOR_SCOPE
    ok=EDITOR_SCOPE.strip()=='[role="dialog"] [contenteditable="true"]'
    return {"ok":ok,"scope":EDITOR_SCOPE}

def check_offline_tests():
    try:
        res=subprocess.run([sys.executable,"-m","pytest","-q","--disable-warnings"],
                           cwd=ROOT_DIR,text=True,capture_output=True,timeout=120)
        return {"ok":res.returncode==0,"returncode":res.returncode,
                "summary":res.stdout.strip().splitlines()[-1] if res.stdout else "pytest failed"}
    except (OSError,subprocess.TimeoutExpired):
        return {"ok":False,"returncode":-1,"summary":"TEST_TIMEOUT_OR_ERROR"}

def checkout_revision():
    try:
        res=subprocess.run(["git","rev-parse","--short=12","HEAD"],cwd=ROOT_DIR,
                           capture_output=True,text=True,timeout=3,check=True)
        return res.stdout.strip()
    except (OSError,subprocess.SubprocessError):
        return None

def check_server_health(port=8108):
    expected=checkout_revision()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health",timeout=3) as conn:
            data=json.load(conn)
        ok=bool(data.get("ok")) and bool(expected) and data.get("build_revision")==expected and data.get("busy") is False
        return {"ok":ok,"server_available":True,"revision_matches":ok,
                "expected_revision":expected,"observed_revision":data.get("build_revision"),
                "busy":data.get("busy"),"pid":data.get("pid")}
    except (OSError,ValueError,TypeError):
        return {"ok":False,"server_available":False,"revision_matches":False,
                "expected_revision":expected}

def evaluate(scope,tests,server=None,dialogs=None,offline=False):
    if not scope.get("ok") or not tests.get("ok"):
        return False
    if offline:
        return True
    return (bool(server and server.get("ok")) and
            bool(dialogs and dialogs.get("status")=="ZERO_MATCHING_DIALOGS_FOUND"))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--offline",action="store_true",
                        help="Apenas testes de código, sem afirmar Chrome/servidor pronto")
    args=parser.parse_args()
    from scripts.check_dialogs import check_open_dialogs
    scope=check_editor_scope_constant()
    tests=check_offline_tests()
    server=None if args.offline else check_server_health()
    dialogs=None if args.offline else check_open_dialogs()
    passed=evaluate(scope,tests,server,dialogs,offline=args.offline)
    print(json.dumps({"scope_safety":scope,"offline_tests":tests,
                      "server_status":server,"win32_dialogs":dialogs,
                      "mode":"OFFLINE_ONLY" if args.offline else "LIVE_PREFLIGHT",
                      "overall_pass":passed},ensure_ascii=False))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
