import pytest
from app.validation import ValidationError, validate_slug, validate_url


@pytest.mark.parametrize("bad", [
    "javascript:alert(1)", "data:text/html,hi", "file:///etc/passwd", "ftp://example.com/x",
    "http://", "http://user:pw@example.com", "http://localhost/x", "http://127.0.0.1/",
    "http://10.0.0.5/", "https://exa mple.com", "",
])
def test_rejects_bad_urls(bad):
    with pytest.raises(ValidationError):
        validate_url(bad)


def test_accepts_normal_url():
    u = "https://example.com/products/summer-sale?utm_source=email"
    assert validate_url(u) == u


def test_rejects_own_host():
    with pytest.raises(ValidationError):
        validate_url("https://sho.rt/abc", own_host="sho.rt")


@pytest.mark.parametrize("slug", ["api", "Admin", "login", "ab", "has space", "x" * 33, "a/b"])
def test_rejects_bad_slugs(slug):
    with pytest.raises(ValidationError):
        validate_slug(slug)


def test_accepts_slug():
    assert validate_slug("summer-sale_1") == "summer-sale_1"
