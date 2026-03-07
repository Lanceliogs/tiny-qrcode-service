import base64
import io

import pytest
from PIL import Image
from httpx import ASGITransport, AsyncClient

from app import app


@pytest.fixture
def tiny_png_b64() -> str:
    """A valid 1x1 white PNG encoded as base64."""
    img = Image.new("RGBA", (1, 1), (255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
