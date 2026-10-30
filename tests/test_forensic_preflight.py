from scripts.verify_scope_safety import evaluate,check_server_health
from scripts.check_dialogs import exit_code

def test_live_preflight_not_green_when_server_offline():
    scope={"ok":True}
    tests={"ok":True}
    assert not evaluate(scope,tests,server={"ok":False},
                        dialogs={"status":"ZERO_MATCHING_DIALOGS_FOUND"})
    assert not evaluate(scope,tests,server={"ok":True},dialogs={"status":"ERROR"})
    assert evaluate(scope,tests,offline=True)

def test_dialog_errors_never_report_clean_exit():
    assert exit_code({"status":"ERROR","found":None})==2
    assert exit_code({"status":"SKIPPED_NON_WINDOWS","found":None})==2
    assert exit_code({"status":"DIALOG_FOUND","found":True})==1
    assert exit_code({"status":"ZERO_MATCHING_DIALOGS_FOUND","found":False})==0
