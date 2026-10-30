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
        # Assinaturas explícitas impedem truncar HWND em Win64.
        user32.EnumWindows.argtypes=[CALLBACK,wintypes.LPARAM]
        user32.EnumWindows.restype=wintypes.BOOL
        user32.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user32.GetClassNameW.restype=ctypes.c_int
        user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user32.GetWindowTextW.restype=ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype=wintypes.DWORD
        user32.IsWindowVisible.argtypes=[wintypes.HWND]
        user32.IsWindowVisible.restype=wintypes.BOOL
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
