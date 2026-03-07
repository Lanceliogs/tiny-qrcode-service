import pytest

from app import _validate_url, _hex_to_rgb


class TestValidateUrl:
    def test_valid_https(self):
        assert _validate_url("https://example.com") is None

    def test_valid_http(self):
        assert _validate_url("http://example.com") is None

    def test_empty(self):
        assert _validate_url("") is not None

    def test_whitespace_only(self):
        assert _validate_url("   ") is not None

    def test_no_scheme(self):
        err = _validate_url("example.com")
        assert err is not None
        assert "http" in err.lower()

    def test_ftp_rejected(self):
        err = _validate_url("ftp://example.com")
        assert err is not None

    def test_no_netloc(self):
        err = _validate_url("https://")
        assert err is not None

    def test_too_long(self):
        err = _validate_url("https://example.com/" + "a" * 2000)
        assert err is not None
        assert "long" in err.lower()


class TestHexToRgb:
    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_white(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_red(self):
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_arbitrary(self):
        assert _hex_to_rgb("#1a2b3c") == (26, 43, 60)
