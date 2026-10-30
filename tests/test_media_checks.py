import pytest
from app.media_checks import (
    caption_matches, gallery_complete, pick_file_input_index, normalize_caption
)

@pytest.mark.parametrize("kind,accepts,wanted",[
    ("image",["image/jpeg,image/png"],0),
    ("video",["image/png","video/mp4,video/quicktime"],1),
    ("image",["video/*",""],1),
    ("image",[],None),
])
def test_select_media_input(kind,accepts,wanted):
    assert pick_file_input_index(accepts,kind)==wanted

@pytest.mark.parametrize("accepts",[
    ["image/*","image/*"],
    ["",""],
])
def test_ambiguous_inputs_fail_closed(accepts):
    with pytest.raises(ValueError):
        pick_file_input_index(accepts,"image")

def test_incompatible_input_fails_closed():
    with pytest.raises(ValueError):
        pick_file_input_index(["video/mp4"],"image")

@pytest.mark.parametrize("count,visible,overflow,assigned,expected",[
    (1,1,None,1,True),
    (2,2,None,2,True),
    (6,6,None,6,True),
    (6,4,2,6,True),
    (6,2,4,6,True),
    (6,2,None,6,False), # 'Editar' is never proof of all files
    (6,4,1,6,False),
    (6,4,2,0,False), # input cleared: gallery alone does not prove all six
    (6,4,2,5,False),
    (10,4,6,10,True),
])
def test_gallery_requires_quantitative_evidence(count,visible,overflow,assigned,expected):
    assert gallery_complete(count,visible,overflow,assigned) is expected

def test_caption_recheck_after_upload():
    assert caption_matches("Fotos de Natal\nTijucas!","Fotos de Natal  Tijucas!")
    assert not caption_matches("Fotos de Natal", "Fotos de")
    assert normalize_caption(" A\u00a0 B ")=="A B"
