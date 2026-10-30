from app.post_state import requires_hold

def test_processing_state_blocks_group_switch():
    assert requires_hold("VIDEO_PROCESSING")
    assert requires_hold("POSTING_IN_PROGRESS")
    assert not requires_hold("PENDING_REVIEW")
