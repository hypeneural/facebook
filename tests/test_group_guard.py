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
