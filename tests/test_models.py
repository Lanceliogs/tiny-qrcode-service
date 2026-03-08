import pytest
from pydantic import ValidationError

from app import QROptions, QRRequest, PageState


# ── QROptions ────────────────────────────────────────────


class TestQROptionsDefaults:
    def test_defaults(self):
        opts = QROptions()
        assert opts.fill_color == "#000000"
        assert opts.bg_color == "#ffffff"
        assert opts.gradient_type == "none"
        assert opts.module_drawer == "square"
        assert opts.logo_b64 is None
        assert opts.box_size == 10
        assert opts.border == 4


class TestQROptionsColors:
    def test_valid_hex_colors(self):
        opts = QROptions(fill_color="#FF00aa", bg_color="#123abc")
        assert opts.fill_color == "#ff00aa"
        assert opts.bg_color == "#123abc"

    @pytest.mark.parametrize("color", ["red", "#xyz", "000000", "#00", "#1234567"])
    def test_invalid_hex_colors(self, color):
        with pytest.raises(ValidationError, match="hex color"):
            QROptions(fill_color=color)

    def test_invalid_bg_color(self):
        with pytest.raises(ValidationError, match="hex color"):
            QROptions(bg_color="not-a-color")

    def test_invalid_gradient_end_color(self):
        with pytest.raises(ValidationError, match="hex color"):
            QROptions(gradient_end_color="nope")


class TestQROptionsEnums:
    @pytest.mark.parametrize("drawer", [
        "square", "rounded", "circle", "gapped", "vertical_bars", "horizontal_bars",
    ])
    def test_valid_module_drawers(self, drawer):
        opts = QROptions(module_drawer=drawer)
        assert opts.module_drawer == drawer

    def test_invalid_module_drawer(self):
        with pytest.raises(ValidationError):
            QROptions(module_drawer="stars")

    @pytest.mark.parametrize("gt", ["none", "radial", "horizontal", "vertical"])
    def test_valid_gradient_types(self, gt):
        opts = QROptions(gradient_type=gt)
        assert opts.gradient_type == gt

    def test_invalid_gradient_type(self):
        with pytest.raises(ValidationError):
            QROptions(gradient_type="diagonal")


class TestQROptionsNumericBounds:
    def test_box_size_min(self):
        with pytest.raises(ValidationError):
            QROptions(box_size=4)

    def test_box_size_max(self):
        with pytest.raises(ValidationError):
            QROptions(box_size=21)

    def test_border_min(self):
        opts = QROptions(border=0)
        assert opts.border == 0

    def test_border_max(self):
        with pytest.raises(ValidationError):
            QROptions(border=9)


class TestQROptionsLogo:
    def test_empty_string_becomes_none(self):
        opts = QROptions(logo_b64="")
        assert opts.logo_b64 is None

    def test_none_stays_none(self):
        opts = QROptions(logo_b64=None)
        assert opts.logo_b64 is None

    def test_valid_png(self, tiny_png_b64):
        opts = QROptions(logo_b64=tiny_png_b64)
        assert opts.logo_b64 == tiny_png_b64

    def test_invalid_base64(self):
        with pytest.raises(ValidationError, match="not valid base64"):
            QROptions(logo_b64="not!valid!base64===")

    def test_valid_base64_but_not_image(self):
        import base64
        data = base64.b64encode(b"just some text, not an image").decode()
        with pytest.raises(ValidationError, match="valid image"):
            QROptions(logo_b64=data)


# ── QRRequest ────────────────────────────────────────────


class TestQRRequest:
    def test_valid_request(self):
        req = QRRequest(link="https://example.com")
        assert str(req.link) == "https://example.com/"
        assert req.options == QROptions()

    def test_with_options(self):
        req = QRRequest(
            link="https://example.com",
            options={"fill_color": "#ff0000", "module_drawer": "circle"},
        )
        assert req.options.fill_color == "#ff0000"
        assert req.options.module_drawer == "circle"

    def test_invalid_link(self):
        with pytest.raises(ValidationError):
            QRRequest(link="not-a-url")

    def test_ftp_link_rejected(self):
        with pytest.raises(ValidationError):
            QRRequest(link="ftp://example.com/file")


# ── PageState ────────────────────────────────────────────


class TestPageState:
    def test_defaults_not_customized(self):
        state = PageState()
        assert state.is_customized is False

    def test_non_default_color_is_customized(self):
        state = PageState(options=QROptions(fill_color="#ff0000"))
        assert state.is_customized is True

    def test_non_default_drawer_is_customized(self):
        state = PageState(options=QROptions(module_drawer="circle"))
        assert state.is_customized is True

    def test_non_default_border_is_customized(self):
        state = PageState(options=QROptions(border=0))
        assert state.is_customized is True

    def test_transparent_bg_is_customized(self):
        state = PageState(options=QROptions(transparent_bg=True))
        assert state.is_customized is True
