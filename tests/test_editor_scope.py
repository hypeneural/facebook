"""Regression for Lexical hydration and comment-field safety, without Facebook."""
import pytest
from app.browser import Browser, EDITOR_SCOPE
from app.telemetry import error_code

class Editor:
    def __init__(self,allowed=True,text=""):
        self.allowed=allowed
        self.text=text
    def is_visible(self):
        return True
    def is_editable(self):
        return True
    def evaluate(self,script):
        if "innerText" in script:
            return self.text
        return self.allowed
    def fill(self,value,**kwargs):
        self.text=value

class Locators:
    def __init__(self,items):
        self.items=items
    def count(self):
        return len(self.items)
    def nth(self,index):
        return self.items[index]

class Page:
    def __init__(self,items):
        self.items=items
        self.selectors=[]
    def locator(self,selector):
        self.selectors.append(selector)
        if selector==EDITOR_SCOPE:
            return Locators(self.items)
        raise AssertionError("A busca vazou para editor global: "+selector)
    def wait_for_timeout(self,ms):
        pass

def make_bot(tmp_path,items):
    bot=Browser(tmp_path/"chrome-profile")
    bot.page=Page(items)
    return bot

def test_only_dialog_editor_is_queried(tmp_path):
    valid=Editor()
    bot=make_bot(tmp_path,[valid])
    try:
        assert bot._find_editor(timeout_ms=0) is valid
        assert bot.page.selectors==[EDITOR_SCOPE]
        assert EDITOR_SCOPE.startswith('[role="dialog"]')
    finally:
        bot.pool.shutdown(wait=False)

def test_comment_editor_is_rejected(tmp_path):
    bot=make_bot(tmp_path,[Editor(allowed=False)])
    try:
        assert bot._find_editor(timeout_ms=0) is None
    finally:
        bot.pool.shutdown(wait=False)

def test_missing_dialog_never_uses_global_fallback(tmp_path):
    bot=make_bot(tmp_path,[])
    try:
        assert bot._find_editor(timeout_ms=0) is None
        assert all(selector.startswith('[role="dialog"]') for selector in bot.page.selectors)
    finally:
        bot.pool.shutdown(wait=False)

def test_multiple_visible_editors_fail_closed(tmp_path):
    bot=make_bot(tmp_path,[Editor(),Editor()])
    try:
        with pytest.raises(ValueError,match="EDITOR_AMBIGUOUS"):
            bot._find_editor(timeout_ms=0)
    finally:
        bot.pool.shutdown(wait=False)

def test_caption_recheck_uses_same_scoped_editor(tmp_path):
    bot=make_bot(tmp_path,[Editor(text="Fotos de Natal")])
    try:
        bot._assert_caption("Fotos de Natal",None)
        with pytest.raises(ValueError,match="CAPTION_LOST_AFTER_UPLOAD"):
            bot._assert_caption("Outra legenda",None)
    finally:
        bot.pool.shutdown(wait=False)

def test_editor_error_codes_are_stable():
    assert error_code("FIND_CAPTION_EDITOR","EDITOR_AMBIGUOUS: two")=="EDITOR_AMBIGUOUS"
    assert error_code("FIND_CAPTION_EDITOR","CAPTION_EDITOR_NOT_FOUND: no editor")=="CAPTION_EDITOR_NOT_FOUND"
