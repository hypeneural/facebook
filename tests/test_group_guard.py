from app.post_state import requires_hold

def test_processing_state_blocks_group_switch():
    assert requires_hold("VIDEO_PROCESSING")
    assert requires_hold("POSTING_IN_PROGRESS")
    assert not requires_hold("PENDING_REVIEW")

import pytest
from app.group_guard import destination_state

@pytest.mark.parametrize("path,status",[
    ("/groups/123456/","GROUP_CONFIRMED"),
    ("/groups/123456/discussion","GROUP_CONFIRMED"),
    ("/groups/999999/","GROUP_MISMATCH"),
    ("/login/","AUTH_OR_CHECKPOINT"),
    ("/checkpoint/","AUTH_OR_CHECKPOINT"),
    ("/","NOT_ON_GROUP"),
])
def test_group_destination_must_match(path,status):
    base="https://www.facebook.com"
    result=destination_state(base+path,base+"/groups/123456/")
    assert result["state"]==status

from app.browser import Browser

class FakePage:
    def __init__(self,url):
        self.url=url
    def goto(self,*args,**kwargs):
        pass
    def is_closed(self):
        return False
    def wait_for_timeout(self,ms):
        pass

@pytest.mark.parametrize("actual,composer,expected",[
    ("https://www.facebook.com/groups/123456/",True,"GROUP_COMPOSER_READY"),
    ("https://www.facebook.com/groups/123456/",False,"GROUP_COMPOSER_NOT_FOUND"),
])
def test_group_open_checks_composer(tmp_path,actual,composer,expected):
    bot=Browser(tmp_path/"chrome-profile")
    bot.page=FakePage(actual)
    bot._post_state=lambda:{"state":"NO_OPERATION"}
    bot._status=lambda:{"logged_in":True}
    bot._find=lambda *args,**kwargs: object() if composer else None
    try:
        result=bot._group("https://www.facebook.com/groups/123456/")
        assert result["state"]==expected
        assert result["destination_verified"]
    finally:
        bot.pool.shutdown(wait=False)

def test_redirect_to_wrong_group_never_passes(tmp_path):
    bot=Browser(tmp_path/"chrome-profile")
    bot.page=FakePage("https://www.facebook.com/groups/999999/")
    bot._post_state=lambda:{"state":"NO_OPERATION"}
    bot._status=lambda:{"logged_in":True}
    try:
        with pytest.raises(ValueError,match="GROUP_DESTINATION_MISMATCH"):
            bot._group("https://www.facebook.com/groups/123456/")
    finally:
        bot.pool.shutdown(wait=False)

def test_invalid_group_outside_facebook():
    from app.group_guard import destination_state
    assert destination_state("https://sample.invalid/groups/123456/")["state"]=="OUTSIDE_FACEBOOK"

def test_publish_wrong_destination_fails_before_submit(tmp_path):
    bot=Browser(tmp_path/"chrome-profile")
    bot.page=FakePage("https://www.facebook.com/groups/999999/")
    bot._post_state=lambda:{"state":"NO_OPERATION"}
    bot._status=lambda:{"logged_in":True}
    try:
        with pytest.raises(ValueError,match="GROUP_DESTINATION_MISMATCH"):
            bot._publish("https://www.facebook.com/groups/123456/","test",[])
        assert bot.last_submission is None
    finally:
        bot.pool.shutdown(wait=False)

def test_selected_profile_is_restored_only_if_registered(tmp_path):
    import json
    (tmp_path/"accounts.json").write_text(json.dumps([{"id":"secondary","name":"Segundo"}]),encoding="utf8")
    (tmp_path/"selected-account.json").write_text(json.dumps({"id":"secondary"}),encoding="utf8")
    bot=Browser(tmp_path/"chrome-profile")
    try:
        assert bot.account_id=="secondary"
        assert bot.root==tmp_path/"profiles"/"secondary"
    finally:
        bot.pool.shutdown(wait=False)
