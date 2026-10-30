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

def test_single_video_deadline_shared_for_preview_and_button():
    from app.media_policy import remaining_budget_ms
    assert remaining_budget_ms(100.0,now=90.0)==10000
    assert remaining_budget_ms(100.0,now=99.5)==1000
    assert remaining_budget_ms(None)==15000

def test_video_budget_scales_bounded_by_size():
    assert wait_budget_ms("video",1,28489566)==240000
    assert 240000<wait_budget_ms("video",1,300*1024*1024)<=600000
    assert wait_budget_ms("video",1,20*1024**3)==600000
