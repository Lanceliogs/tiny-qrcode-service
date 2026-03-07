import pytest

from app import app


# ── Web routes ───────────────────────────────────────────


@pytest.mark.anyio
async def test_get_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "QR Code Generator" in resp.text


@pytest.mark.anyio
async def test_post_generate_valid(client):
    resp = await client.post("/", data={"link": "https://example.com"})
    assert resp.status_code == 200
    assert "data:image/png;base64," in resp.text


@pytest.mark.anyio
async def test_post_generate_invalid_url(client):
    resp = await client.post("/", data={"link": "not-a-url"})
    assert resp.status_code == 200
    assert "Only http" in resp.text


@pytest.mark.anyio
async def test_post_generate_with_options(client):
    resp = await client.post("/", data={
        "link": "https://example.com",
        "fill_color": "#ff0000",
        "module_drawer": "circle",
        "box_size": "8",
        "border": "2",
    })
    assert resp.status_code == 200
    assert "data:image/png;base64," in resp.text


@pytest.mark.anyio
async def test_download(client):
    resp = await client.post("/download", data={"link": "https://example.com"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:4] == b"\x89PNG"


@pytest.mark.anyio
async def test_download_invalid_url(client):
    resp = await client.post("/download", data={"link": "ftp://bad"})
    assert resp.status_code == 400


# ── API routes ───────────────────────────────────────────


@pytest.mark.anyio
async def test_api_generate_minimal(client):
    resp = await client.post(
        "/api/generate",
        json={"link": "https://example.com"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:4] == b"\x89PNG"


@pytest.mark.anyio
async def test_api_generate_with_options(client):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {
                "fill_color": "#1a1a2e",
                "gradient_type": "radial",
                "gradient_end_color": "#e94560",
                "module_drawer": "circle",
                "box_size": 15,
                "border": 2,
            },
        },
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"\x89PNG"


@pytest.mark.anyio
async def test_api_generate_with_logo(client, tiny_png_b64):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {"logo_b64": tiny_png_b64},
        },
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"\x89PNG"


@pytest.mark.anyio
async def test_api_generate_invalid_url(client):
    resp = await client.post(
        "/api/generate",
        json={"link": "not-a-url"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_api_generate_invalid_color(client):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {"fill_color": "red"},
        },
    )
    assert resp.status_code == 422
    assert "hex color" in resp.text


@pytest.mark.anyio
async def test_api_generate_invalid_drawer(client):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {"module_drawer": "stars"},
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_api_generate_invalid_logo(client):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {"logo_b64": "not-valid-base64!!!"},
        },
    )
    assert resp.status_code == 422
    assert "base64" in resp.text


@pytest.mark.anyio
async def test_api_generate_box_size_out_of_range(client):
    resp = await client.post(
        "/api/generate",
        json={
            "link": "https://example.com",
            "options": {"box_size": 50},
        },
    )
    assert resp.status_code == 422
