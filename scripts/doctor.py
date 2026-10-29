"""Preflight offline sem acesso ao Facebook nem leitura de credenciais."""
from __future__ import annotations
import argparse
import importlib.util
import json
import platform
import sys
import urllib.request


def diagnose(offline: bool = False):
    modules = {n: importlib.util.find_spec(n) is not None for n in ("fastapi", "uvicorn", "playwright", "multipart")}
    facts = {
        "python": platform.python_version(),
        "python_ok": sys.version_info >= (3, 10),
        "modules": modules,
        "real_facebook_publish_verified": False,
    }
    if not offline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8108/health", timeout=2) as res:
                facts["server_ready"] = bool(json.load(res).get("ok"))
        except (OSError, ValueError):
            facts["server_ready"] = False
    return facts, facts["python_ok"] and all(modules.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Sem conexoes de rede")
    args = parser.parse_args()
    facts, ok = diagnose(offline=args.offline)
    print(json.dumps({"ready": ok, **facts}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
