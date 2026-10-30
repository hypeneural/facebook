import pytest
from app.media_policy import media_kind,wait_budget_ms,preview_selector

def test_media_types():
    assert media_kind([])=="text"
    assert media_kind(["a.PNG","b.jpg","c.webp"])=="image"
    assert media_kind(["clip.MP4"])=="video"
    with pytest.raises(ValueError):media_kind(["a.jpg","b.mp4"])

def test_timeouts_and_preview():
    assert wait_budget_ms("video",1)>wait_budget_ms("image",10)
    assert wait_budget_ms("image",10)>wait_budget_ms("image",1)
    assert "video" in preview_selector("video")
