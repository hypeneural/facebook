import pytest
from app.post_state import classify_post_ui, POST_UI_JS

@pytest.mark.parametrize("signals,expected",[
    ({"posting":True,"dialog_open":True},"POSTING_IN_PROGRESS"),
    ({"video_processing":True},"VIDEO_PROCESSING"),
    ({"pending_review":True,"dialog_open":True},"PENDING_REVIEW"),
    ({"warning":True,"posting":True},"FACEBOOK_WARNING"),
    ({"dialog_open":True},"DIALOG_OPEN_UNVERIFIED"),
    ({}, "POST_UI_CLOSED_UNVERIFIED"),
    (None,"OBSERVATION_UNAVAILABLE"),
])
def test_post_state_is_conservative(signals,expected):
    assert classify_post_ui(signals)==expected

def test_no_posted_success_from_closed_dialog():
    assert classify_post_ui({"dialog_open":False})!="VERIFIED_EXTERNALLY"

def test_js_returns_only_flags_not_caption_or_cookies():
    assert "return {dialog_open:" in POST_UI_JS
    assert "cookie" not in POST_UI_JS
    assert "postando" in POST_UI_JS.lower()
