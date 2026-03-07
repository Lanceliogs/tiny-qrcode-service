from __future__ import annotations

import io
import base64
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path

import asyncio
import logging

import qrcode
import uvicorn
from PIL import Image

from fastapi import FastAPI, Form, Request, Response, HTTPException
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

MODULE_DRAWERS = {
    "square": SquareModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
    "gapped": GappedSquareModuleDrawer,
    "vertical_bars": VerticalBarsDrawer,
    "horizontal_bars": HorizontalBarsDrawer,
}

GRADIENT_TYPES = {"none", "radial", "horizontal", "vertical"}


@dataclass
class QROptions:
    fill_color: str = "#000000"
    bg_color: str = "#ffffff"
    gradient_type: str = "none"
    gradient_end_color: str = "#0000ff"
    module_drawer: str = "square"
    logo_b64: Optional[str] = None
    box_size: int = 10
    border: int = 4


@dataclass
class PageState:
    value: str = ""
    error: Optional[str] = None
    png_b64: Optional[str] = None
    fill_color: str = "#000000"
    bg_color: str = "#ffffff"
    gradient_type: str = "none"
    gradient_end_color: str = "#0000ff"
    module_drawer: str = "square"
    logo_b64: Optional[str] = None
    box_size: int = 10
    border: int = 4

    @property
    def is_customized(self) -> bool:
        return (
            self.module_drawer != "square"
            or self.fill_color != "#000000"
            or self.bg_color != "#ffffff"
            or self.gradient_type != "none"
            or self.logo_b64 is not None
            or self.box_size != 10
            or self.border != 4
        )


root_path = Path(__file__).parent
app = FastAPI(title="QRCode Service")
app.mount("/static", StaticFiles(directory=root_path / "static"), name="static")
templates = Jinja2Templates(directory=root_path / "templates")


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


def _parse_qr_options(
    fill_color: str,
    bg_color: str,
    gradient_type: str,
    gradient_end_color: str,
    module_drawer: str,
    logo_b64: str,
    box_size: int,
    border: int,
) -> QROptions:
    return QROptions(
        fill_color=fill_color,
        bg_color=bg_color,
        gradient_type=gradient_type if gradient_type in GRADIENT_TYPES else "none",
        gradient_end_color=gradient_end_color,
        module_drawer=module_drawer if module_drawer in MODULE_DRAWERS else "square",
        logo_b64=logo_b64 or None,
        box_size=max(5, min(20, box_size)),
        border=max(0, min(8, border)),
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    state = PageState()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": state},
    )


@app.post("/", response_class=HTMLResponse)
async def generate(
    request: Request,
    link: str = Form(...),
    fill_color: str = Form("#000000"),
    bg_color: str = Form("#ffffff"),
    gradient_type: str = Form("none"),
    gradient_end_color: str = Form("#0000ff"),
    module_drawer: str = Form("square"),
    logo_b64: str = Form(""),
    box_size: int = Form(10),
    border: int = Form(4),
):
    err = _validate_url(link)
    opts = _parse_qr_options(
        fill_color, bg_color, gradient_type, gradient_end_color,
        module_drawer, logo_b64, box_size, border,
    )

    state = PageState(
        value=link.strip(),
        error=err,
        fill_color=opts.fill_color,
        bg_color=opts.bg_color,
        gradient_type=opts.gradient_type,
        gradient_end_color=opts.gradient_end_color,
        module_drawer=opts.module_drawer,
        logo_b64=opts.logo_b64,
        box_size=opts.box_size,
        border=opts.border,
    )

    if err:
        logger.error("Invalid URL")
        raise HTTPException(status_code=400, detail="invalid url")

    png = await asyncio.to_thread(_make_qr_png, state.value, opts)
    state.png_b64 = base64.b64encode(png).decode("ascii")

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": state},
    )


@app.post("/download")
async def download(
    link: str = Form(...),
    fill_color: str = Form("#000000"),
    bg_color: str = Form("#ffffff"),
    gradient_type: str = Form("none"),
    gradient_end_color: str = Form("#0000ff"),
    module_drawer: str = Form("square"),
    logo_b64: str = Form(""),
    box_size: int = Form(10),
    border: int = Form(4),
):
    err = _validate_url(link)
    if err:
        return Response(content=err, status_code=400, media_type="text/plain")

    opts = _parse_qr_options(
        fill_color, bg_color, gradient_type, gradient_end_color,
        module_drawer, logo_b64, box_size, border,
    )
    png = _make_qr_png(link.strip(), opts)

    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="qrcode.png"'},
    )


def main():
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
