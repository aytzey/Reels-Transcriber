# Reels Transcriber

GPU-accelerated speech-to-text pipeline for Instagram Reels and TikTok videos using OpenAI Whisper Large-v3.

Enter a username or paste a video URL. The pipeline downloads the videos, extracts audio, runs batched inference on your GPU, and returns full transcripts. No login required for either platform.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![CUDA](https://img.shields.io/badge/CUDA-supported-brightgreen)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-supported-brightgreen)

## Features

- **Instagram Reels** — transcribe all reels from a profile or a single reel URL
- **TikTok Videos** — transcribe all videos from a profile or a single video URL
- **Whisper Large-v3** with SDPA attention — no Flash Attention dependency
- **Hardware-aware inference** — auto-detects CUDA / Apple Silicon (MPS) / CPU, sets optimal dtype and batch size
- **No login required** — works with public profiles on both platforms
- **Proxy CDN download** — works behind corporate firewalls and SSL-inspecting proxies
- **Batch file upload** — drag-and-drop your own video/audio files
- **15+ languages** — auto-detection or manual selection
- **Export** — JSON and TXT download

## Performance

Benchmarked on a real Instagram profile (12 reels, ~50 MB total video):

| Hardware | Transcription time | Per-reel average |
|---|---|---|
| RTX 3060 12 GB (CUDA, float16, batch 16) | **168 s** | **14 s** |
| Apple M2 Pro (MPS, float32, batch 8) | ~5 min | ~25 s |
| CPU-only (float32, batch 4) | ~20 min | ~100 s |

## Quick start

```bash
git clone https://github.com/aytzey/reels-transcriber.git
cd reels-transcriber

pip install -r requirements.txt
playwright install chromium

python app.py
```

Open **http://localhost:7860** in your browser.
The model (~3 GB) downloads automatically on first run.

### Platform-specific setup

**macOS (Apple Silicon)**
```bash
pip install -r requirements.txt
playwright install chromium
```

**Linux / Windows (NVIDIA GPU)**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
playwright install chromium
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Gradio Web UI                             │
│  ┌──────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │Single URL│ │IG Profile  │ │TikTok Profile│ │Upload Files  │ │
│  └────┬─────┘ └─────┬──────┘ └──────┬───────┘ └──────┬───────┘ │
└───────┼─────────────┼───────────────┼────────────────┼──────────┘
        │             │               │                │
        ▼             ▼               ▼                │
   ┌─────────┐  ┌──────────┐  ┌───────────┐           │
   │IG: igram│  │IG: igram │  │TT: tikwm  │           │
   │TT: tikwm│  │ profile  │  │ profile   │           │
   │ convert │  │ scrape   │  │ scrape    │           │
   └────┬────┘  └────┬─────┘  └─────┬─────┘           │
        │             │              │                  │
        └──────────┬──┴──────────────┘                  │
                   ▼                                    ▼
        ┌─────────────────────────────────────────────────────┐
        │                  transcriber.py                       │
        │  ffmpeg (16 kHz WAV) → Whisper Large-v3              │
        │  30s chunks × batch_size → SDPA attention            │
        └──────────────────────┬──────────────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────────────┐
        │  formatter.py  →  Markdown  ·  JSON  ·  TXT         │
        └─────────────────────────────────────────────────────┘

Hardware abstraction (device.py):
  CUDA  →  float16, batch 16–24
  MPS   →  float32, batch 8
  CPU   →  float32, batch 4
```

## How it works

**Instagram** — Playwright drives a headless Chromium browser to a web service (igram.world). It intercepts API responses to get post lists (with cursor-based pagination) and signed proxy CDN URLs for each video. Downloads go through the proxy, so the pipeline works even behind firewalls that block `cdninstagram.com`.

**TikTok** — Single videos are downloaded via the tikwm.com API (no auth, no Cloudflare). Profile scraping uses Playwright to call tikwm's user/posts endpoint from within a browser context to bypass Cloudflare Turnstile. Video bytes are proxied through tikwm's CDN.

**Transcription** — Each video is converted to 16 kHz mono WAV via ffmpeg. Whisper splits audio into 30-second chunks and processes `batch_size` chunks in parallel. SDPA (Scaled Dot-Product Attention) is used across all backends — it's PyTorch-native and equivalent to Flash Attention 2 with zero external dependencies.

**Why float32 on MPS?** — Whisper's cross-attention layers can produce NaN with float16 on Apple's MPS backend in PyTorch ≤2.3. Using float32 is ~1.5x slower but guarantees correct output.

## Project structure

```
├── app.py                          # Gradio UI + pipeline orchestration
├── reels_transcriber/
│   ├── device.py                   # Hardware detection (CUDA / MPS / CPU)
│   ├── transcriber.py              # Whisper pipeline, audio extraction, batched inference
│   ├── scraper.py                  # Instagram: profile scraper + single reel download
│   ├── tiktok.py                   # TikTok: profile scraper + single video download
│   └── formatter.py                # Markdown / JSON / TXT export
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```

## Device support

| Platform | Device | Dtype | Batch size | Notes |
|---|---|---|---|---|
| Linux / Windows | NVIDIA GPU (CUDA) | float16 | 8–24 (scales with VRAM) | Fastest |
| macOS | Apple Silicon (MPS) | float32 | 8 | M1/M2/M3/M4 |
| Any | CPU | float32 | 4 | Slow but works everywhere |

## Requirements

| Dependency | Purpose |
|---|---|
| `torch` + `torchaudio` | Inference engine |
| `transformers` | Whisper pipeline |
| `gradio` | Web interface |
| `playwright` | Headless browser for scraping |
| `requests` | TikTok API calls |
| `ffmpeg` (system) | Audio extraction |

## License

MIT
