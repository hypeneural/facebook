"""Verificador automatizado de integridade forense da PR #6 (Escopo do Editor Lexical).
Valida suíte offline de testes, restrição de escopo de seletores e ausência de janelas Win32.
"""
from __future__ import annotations
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

# Garante import do projeto mesmo se executado de outro diretório
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def check_editor_scope_constant() -> dict:
    from app.browser import EDITOR_SCOPE
    starts_dialog = EDITOR_SCOPE.startswith('[role="dialog"]')
    no_global = "contenteditable" not in EDITOR_SCOPE or starts_dialog
    has_global_fallback = any(
        s.strip() in ("[contenteditable='true']", '[contenteditable="true"]')
        for s in EDITOR_SCOPE.split(",")
    )
    ok = starts_dialog and not has_global_fallback
    return {
        "editor_scope": EDITOR_SCOPE,
        "starts_with_dialog": starts_dialog,
        "has_global_fallback": has_global_fallback,
        "ok": ok
    }

def check_offline_tests() -> dict:
    cmd = [sys.executable, "-m", "pytest", "-q", "--disable-warnings"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    passed = res.returncode == 0
    return {
        "ok": passed,
        "returncode": res.returncode,
        "output_summary": res.stdout.strip().splitlines()[-1] if res.stdout else res.stderr.strip()
    }

def check_server_health(port: int = 8108) -> dict:
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"server_available": True, "health": data}
    except Exception as exc:
        return {"server_available": False, "error": str(exc)}

def main() -> int:
    from scripts.check_dialogs import check_open_dialogs
    
    scope_check = check_editor_scope_constant()
    dialog_check = check_open_dialogs()
    tests_check = check_offline_tests()
    health_check = check_server_health()

    report = {
        "scope_safety": scope_check,
        "win32_dialogs": dialog_check,
        "offline_tests": tests_check,
        "server_status": health_check,
        "overall_pass": bool(
            scope_check["ok"] and not dialog_check.get("found") and tests_check["ok"]
        )
    }

    print(json.dumps(report, indent=2))
    return 0 if report["overall_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
