"""Verificador forense de janelas nativas de arquivos do Windows (#32770, 'Abrir').
Execução offline e segura via ctypes Win32.
"""
from __future__ import annotations
import json
import sys

def check_open_dialogs() -> dict:
    if sys.platform != "win32":
        return {"status": "SKIPPED_NON_WINDOWS", "found": False, "handle": 0}
    try:
        import ctypes
        handle = ctypes.windll.user32.FindWindowW("#32770", "Abrir")
        found = bool(handle != 0)
        return {
            "status": "DIALOG_FOUND" if found else "ZERO_DIALOGS_FOUND",
            "found": found,
            "handle": int(handle)
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc), "found": False, "handle": 0}

def main() -> int:
    result = check_open_dialogs()
    print(json.dumps(result, indent=2))
    return 1 if result.get("found") else 0

if __name__ == "__main__":
    raise SystemExit(main())
