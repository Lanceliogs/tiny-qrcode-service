# Tiny QR Code Generator

A single-page QR code generator with customization options, built with FastAPI and deployed on Vercel.

**Live demo:** https://tiny-qrcode-service.vercel.app/

## Features

- **Module styles** — Square, rounded, circle, gapped, vertical bars, horizontal bars
- **Custom colors** — Pick any fill and background color
- **Gradients** — Radial, horizontal, or vertical gradient effects
- **Logo embedding** — Upload an image to place in the center of the QR code (error correction auto-adjusts)
- **Size controls** — Adjust module size and border width
- **PNG export** — Download the generated QR code as a PNG file

## Stack

- **Backend:** Python 3.12, FastAPI, Jinja2, [python-qrcode](https://github.com/lincolnloop/python-qrcode), Pillow
- **Frontend:** Vanilla HTML/CSS/JS — no framework, no build step
- **Deployment:** Vercel (serverless Python)

## Run locally

```bash
# Install dependencies
poetry install

# Start the dev server
poetry run start-app
```

The app will be available at `http://127.0.0.1:8000`.

## Deploy to Vercel

The project is configured for Vercel's Python runtime. `pyproject.toml` is in `.vercelignore` so Vercel picks up `requirements.txt` directly.

```bash
vercel --prod
```

## Project structure

```
├── app.py                 # FastAPI application
├── templates/
│   └── index.html         # Jinja2 template
├── static/
│   ├── style.css          # Styles
│   ├── main.js            # Client-side logic
│   └── favicon.svg        # Favicon
├── pyproject.toml          # Poetry config
├── requirements.txt        # Pinned deps for Vercel
└── .vercelignore           # Hides pyproject.toml from Vercel
```

## License

See [LICENSE](LICENSE).

## Author

Julien Lancelot — [GitHub](https://github.com/Lanceliogs)
