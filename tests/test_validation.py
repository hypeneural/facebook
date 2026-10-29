import pytest
from app.validation import group_url,validate
@pytest.mark.parametrize("bad",["http://facebook.com/groups/123","https://evil.com/groups/123","https://facebook.com.evil.com/groups/123","https://www.facebook.com/pages/123","https://user:pwd@facebook.com/groups/123"])
def test_reject(bad):
    with pytest.raises(ValueError):group_url(bad)
def test_good():
    assert group_url("https://www.facebook.com/groups/1234?ref=share")=="https://www.facebook.com/groups/1234/"
    assert validate("https://www.facebook.com/groups/1234","legenda",[])=="https://www.facebook.com/groups/1234/"
def test_media():
    with pytest.raises(ValueError):validate("https://www.facebook.com/groups/1234","",["a.mp4","b.jpg"])
    with pytest.raises(ValueError):validate("https://www.facebook.com/groups/1234","",["password.txt"])
    with pytest.raises(ValueError):validate("https://www.facebook.com/groups/1234","",[])
