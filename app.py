import binascii
import io
import re
import base64
from typing import Literal, Optional
from urllib.parse import urlparse
from pathlib import Path

import asyncio
import logging

import qrcode
import uvicorn
from PIL import Image
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

from fastapi import FastAPI, Depends, Form, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import (
    SquareModuleDrawer,
    GappedSquareModuleDrawer,
    CircleModuleDrawer,
    RoundedModuleDrawer,
    VerticalBarsDrawer,
    HorizontalBarsDrawer,
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask,
    RadialGradiantColorMask,
    HorizontalGradiantColorMask,
    VerticalGradiantColorMask,
)


logging.basicConfig()
logger = logging.getLogger(__name__)

# ── Types & constants ────────────────────────────────────

ModuleDrawerType = Literal[
    "square", "rounded", "circle", "gapped", "vertical_bars", "horizontal_bars",
]
GradientType = Literal["none", "radial", "horizontal", "vertical"]

MODULE_DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
    "gapped": GappedSquareModuleDrawer,
    "vertical_bars": VerticalBarsDrawer,
    "horizontal_bars": HorizontalBarsDrawer,
}

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

IMAGE_SIGNATURES = (
    b"\x89PNG",      # PNG
    b"\xff\xd8\xff",  # JPEG
    b"GIF8",          # GIF87a / GIF89a
    b"RIFF",          # WebP (RIFF container)
    b"BM",            # BMP
)

# ── Pydantic models ─────────────────────────────────────


class QROptions(BaseModel):
    fill_color: str = "#000000"
    bg_color: str = "#ffffff"
    gradient_type: GradientType = "none"
    gradient_end_color: str = "#0000ff"
    module_drawer: ModuleDrawerType = "square"
    logo_b64: Optional[str] = None
    box_size: int = Field(default=10, ge=5, le=20)
    border: int = Field(default=4, ge=0, le=8)

    @field_validator("fill_color", "bg_color", "gradient_end_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not HEX_COLOR_RE.match(v):
            raise ValueError("must be a hex color like #ff00aa")
        return v.lower()

    @field_validator("logo_b64", mode="before")
    @classmethod
    def validate_logo(cls, v: str | None) -> str | None:
        if not v:
            return None
        try:
            data = base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("logo_b64 is not valid base64")
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("logo must be under 2 MB")
        if not any(data[:8].startswith(sig) for sig in IMAGE_SIGNATURES):
            raise ValueError("logo must be a valid image (PNG, JPEG, GIF, WebP, or BMP)")
        return v


class QRRequest(BaseModel):
    """JSON body for the API endpoint."""
    link: HttpUrl
    options: QROptions = Field(default_factory=QROptions)


class PageState(BaseModel):
    """Template rendering context."""
    value: str = ""
    error: Optional[str] = None
    png_b64: Optional[str] = None
    options: QROptions = Field(default_factory=QROptions)

    @property
    def is_customized(self) -> bool:
        return self.options != QROptions()


# ── App setup ────────────────────────────────────────────

root_path = Path(__file__).parent
app = FastAPI(title="QRCode Service")
app.mount("/static", StaticFiles(directory=root_path / "static"), name="static")
templates = Jinja2Templates(directory=root_path / "templates")

# ── Core logic ───────────────────────────────────────────


def _validate_url(value: str) -> Optional[str]:
    v = (value or "").strip()
    if not v:
        return "Please paste a link."
    if len(v) > 2000:
        return "That link is too long."
    p = urlparse(v)
    if p.scheme not in ("http", "https"):
        return "Only http(s) links are allowed."
    if not p.netloc:
        return "That doesn't look like a valid URL."
    return None


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _build_color_mask(opts: QROptions):
    fill_rgb = _hex_to_rgb(opts.fill_color)
    bg_rgb = _hex_to_rgb(opts.bg_color)
    end_rgb = _hex_to_rgb(opts.gradient_end_color)

    if opts.gradient_type == "radial":
        return RadialGradiantColorMask(
            back_color=bg_rgb, center_color=fill_rgb, edge_color=end_rgb,
        )
    if opts.gradient_type == "horizontal":
        return HorizontalGradiantColorMask(
            back_color=bg_rgb, left_color=fill_rgb, right_color=end_rgb,
        )
    if opts.gradient_type == "vertical":
        return VerticalGradiantColorMask(
            back_color=bg_rgb, top_color=fill_rgb, bottom_color=end_rgb,
        )
    return SolidFillColorMask(back_color=bg_rgb, front_color=fill_rgb)


def _make_qr_png(value: str, opts: QROptions) -> bytes:
    error_correction = (
        qrcode.constants.ERROR_CORRECT_H
        if opts.logo_b64
        else qrcode.constants.ERROR_CORRECT_M
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=opts.box_size,
        border=opts.border,
    )
    qr.add_data(value)
    qr.make(fit=True)

    drawer_cls = MODULE_DRAWERS.get(opts.module_drawer, SquareModuleDrawer)

    img_kwargs: dict = {
        "image_factory": StyledPilImage,
        "module_drawer": drawer_cls(),
        "color_mask": _build_color_mask(opts),
    }

    if opts.logo_b64:
        logo_bytes = base64.b64decode(opts.logo_b64)
        logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        img_kwargs["embedded_image"] = logo_img

    img = qr.make_image(**img_kwargs)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Form dependency ──────────────────────────────────────


async def _form_options(
    fill_color: str = Form("#000000"),
    bg_color: str = Form("#ffffff"),
    gradient_type: str = Form("none"),
    gradient_end_color: str = Form("#0000ff"),
    module_drawer: str = Form("square"),
    logo_b64: str = Form(""),
    box_size: int = Form(10),
    border: int = Form(4),
) -> QROptions:
    try:
        return QROptions(
            fill_color=fill_color,
            bg_color=bg_color,
            gradient_type=gradient_type,
            gradient_end_color=gradient_end_color,
            module_drawer=module_drawer,
            logo_b64=logo_b64,
            box_size=box_size,
            border=border,
        )
    except ValidationError:
        return QROptions()


# ── Web routes ───────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    state = PageState()
    return templates.TemplateResponse(request, "index.html", {"state": state})


@app.post("/", response_class=HTMLResponse)
async def generate(
    request: Request,
    link: str = Form(...),
    opts: QROptions = Depends(_form_options),
):
    err = _validate_url(link)
    if err:
        state = PageState(value=link.strip(), error=err, options=opts)
        return templates.TemplateResponse(request, "index.html", {"state": state})

    value = link.strip()
    png = await asyncio.to_thread(_make_qr_png, value, opts)
    state = PageState(
        value=value,
        options=opts,
        png_b64=base64.b64encode(png).decode("ascii"),
    )

    return templates.TemplateResponse(request, "index.html", {"state": state})


@app.post("/download")
async def download(
    link: str = Form(...),
    opts: QROptions = Depends(_form_options),
):
    err = _validate_url(link)
    if err:
        return Response(content=err, status_code=400, media_type="text/plain")

    png = await asyncio.to_thread(_make_qr_png, link.strip(), opts)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="qrcode.png"'},
    )


# ── API routes ───────────────────────────────────────────


@app.post(
    "/api/generate",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    summary="Generate a QR code",
)
async def api_generate(body: QRRequest):
    """Accept a JSON body with a URL and options, return a QR code PNG."""
    png = await asyncio.to_thread(_make_qr_png, str(body.link), body.options)
    return Response(content=png, media_type="image/png")


# ── Entry point ──────────────────────────────────────────


def main():
    uvicorn.run("app:app", host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
