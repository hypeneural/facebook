"""Diagnóstico limitado a modais 'Abrir/Open' da sessão Windows interativa.

NÃO é varredura completa de todos os diálogos nem atesta o estado do Facebook.
Falhas da API Win32 são ERRO (exit 2), nunca 'zero diálogos'.
"""
from __future__ import annotations
import json
import sys

def check_open_dialogs():
    if sys.platform!="win32":
        return {"status":"SKIPPED_NON_WINDOWS","found":None,"count":None}
    try:
        import ctypes
        from ctypes import wintypes
        user32=ctypes.windll.user32
        found=[]
        CALLBACK=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        def inspect(hwnd,_):
            cl=ctypes.create_unicode_buffer(256)
            title=ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd,cl,256)
            user32.GetWindowTextW(hwnd,title,256)
            if cl.value=="#32770" and title.value.lower().strip() in {"abrir","open"} and user32.IsWindowVisible(hwnd):
                pid=wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
                found.append({"pid":int(pid.value)})
            return True
        callback=CALLBACK(inspect)
        if not user32.EnumWindows(callback,0):
            return {"status":"ERROR","found":None,"count":None}
        return {"status":"DIALOG_FOUND" if found else "ZERO_MATCHING_DIALOGS_FOUND",
                "found":bool(found),"count":len(found),"processes":found,
                "scope":"visible desktop modals titled Abrir/Open; not scoped to Chromium"}
    except Exception:
        return {"status":"ERROR","found":None,"count":None}

def exit_code(result):
    if result.get("status") in {"ERROR","SKIPPED_NON_WINDOWS"}:
        return 2
    return 1 if result.get("found") else 0

def main():
    result=check_open_dialogs()
    print(json.dumps(result,ensure_ascii=False))
    return exit_code(result)

if __name__=="__main__":
    raise SystemExit(main())
