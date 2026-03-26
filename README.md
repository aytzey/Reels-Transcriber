# Reels Transcriber

Transcribe all public Instagram Reels from any profile — automatically.

Enter a username, and the app downloads every public reel, runs each through
**Whisper Large-v3**, and gives you the full text. Export as JSON or TXT.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- **One-click profile transcription** — enter a username, get every reel as text
- **Whisper Large-v3** — state-of-the-art speech recognition
- **GPU accelerated** — NVIDIA CUDA, Apple Silicon (MPS), or CPU
- **Auto language detection** — or pick from 10+ languages manually
- **Batch file upload** — drag & drop your own video/audio files
- **Export** — download results as JSON or TXT
- **No Instagram login required** — works with any public profile

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/reels-transcriber.git
cd reels-transcriber

pip install -r requirements.txt
playwright install chromium

python app.py
```

Open **http://localhost:7860** in your browser.

## Requirements

| Dependency | Why |
|---|---|
| `torch` + `torchaudio` | Model inference |
| `transformers` | Whisper pipeline |
| `gradio` | Web UI |
| `playwright` | Instagram scraping |
| `ffmpeg` (system) | Audio extraction |

### Install on Mac (Apple Silicon)

```bash
# PyTorch with MPS support ships by default
pip install -r requirements.txt
playwright install chromium
```

### Install on Linux / Windows (NVIDIA GPU)

```bash
# Install PyTorch with CUDA — see https://pytorch.org/get-started
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
playwright install chromium
```

## How it works

```
Username
   │
   ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Scrape profile  │────▶│  Download reels   │────▶│  Whisper v3      │
│  (Playwright)    │     │  (proxy CDN)      │     │  transcription   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                                   Markdown / JSON / TXT
```

1. **Scrape** — Playwright drives a headless browser to list all posts from the profile
2. **Download** — each reel video is fetched through a CDN proxy
3. **Transcribe** — audio is extracted with ffmpeg and fed to Whisper Large-v3
4. **Format** — results are displayed in the UI and saved as JSON + TXT

## Device support

| Platform | Device | Dtype | Notes |
|---|---|---|---|
| Linux / Windows | NVIDIA GPU (CUDA) | float16 | Fastest. Batch size scales with VRAM |
| macOS | Apple Silicon (MPS) | float32 | Works great on M1/M2/M3/M4 |
| Any | CPU | float32 | Slow but works everywhere |

The app auto-detects the best available device at startup.

## Project structure

```
├── app.py                        # Entry point + Gradio UI
├── reels_transcriber/
│   ├── __init__.py
│   ├── device.py                 # Hardware detection (CUDA / MPS / CPU)
│   ├── transcriber.py            # Whisper pipeline + audio extraction
│   ├── scraper.py                # Instagram reel download via Playwright
│   └── formatter.py              # Output formatting (MD / JSON / TXT)
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```

## License

MIT
