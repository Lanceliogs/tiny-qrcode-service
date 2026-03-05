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

from fastapi import FastAPI, Form, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


logging.basicConfig()
logger = logging.getLogger(__name__)

@dataclass
class PageState:
    value: str = ""
    error: Optional[str] = None
    png_b64: Optional[str] = None


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


def _make_qr_png(value: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(value)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    state = PageState()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": state},
    )


@app.post("/", response_class=HTMLResponse)
async def generate(request: Request, link: str = Form(...)):
    err = _validate_url(link)
    state = PageState(value=link.strip(), error=err)

    if err:
        logger.error("Invalid URL")
        raise HTTPException(status_code=400, detail="invalid url")

    png = await asyncio.to_thread(_make_qr_png, state.value)
    state.png_b64 = base64.b64encode(png).decode("ascii")

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": state},
    )


@app.post("/download")
async def download(link: str = Form(...)):
    err = _validate_url(link)
    if err:
        # 400 with a plain message (simple and sufficient)
        return Response(content=err, status_code=400, media_type="text/plain")

    png = _make_qr_png(link.strip())
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="qrcode.png"'},
    )


def main():
    uvicorn.run("tiny_qrcode_service.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()