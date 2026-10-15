import pytest

from app.order_delivery import validate_album_url


@pytest.mark.parametrize("url", [
    "https://photos.app.goo.gl/Ab12",
    "https://photos.google.com/share/Ab_c-1?key=Ab%2Bcd",
    "https://photos.app.goo.gl:443/Ab12?utm_source=test",
    "https://drive.google.com/file/d/Ab_c-1/view?usp=sharing",
    "https://1drv.ms/u/s!Ab_c-1?e=xyz",
    "https://files.acme-cloud.example.com/share/Ab_c-1#access-token",
])
def test_valid_urls_preserve_access_parameters(url):
    assert validate_album_url(f"  {url}  ") == url


@pytest.mark.parametrize("url", [None, "", "   "])
def test_empty_removes(url):
    assert validate_album_url(url) is None


@pytest.mark.parametrize("url", [
    "http://photos.app.goo.gl/Ab12", "javascript:alert(1)",
    "https://photos.app.goo.gl.attacker.test/Ab12", "https://storage.invalid/share/Ab12",
    "https://user@photos.app.goo.gl/Ab12", "https://photos.app.goo.gl:444/Ab12",
    "https://photos.app.goo.gl/", "https://share.example.com",
    "https://photos.app.goo.gl/Ab12\n",
    "https://photos.app.goo.gl\\@attacker.test/Ab12", "https://photos.app.goo.gl/Ab 12",
    "https://127.0.0.1/share/Ab12", "https://localhost/share/Ab12",
    "https://private.internal/share/Ab12",
    "https://photos.app.goo.gl/" + "a" * 2048,
])
def test_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        validate_album_url(url)
