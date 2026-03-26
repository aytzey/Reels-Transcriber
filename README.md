# Reels Transcriber

GPU-accelerated speech-to-text pipeline that transcribes all public Instagram Reels from any profile using OpenAI's Whisper Large-v3.

Enter a username. The pipeline scrapes every public reel, downloads the videos through a proxy CDN, extracts audio, runs batched inference on your GPU, and returns full transcripts. No Instagram login required.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![CUDA](https://img.shields.io/badge/CUDA-supported-brightgreen)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-supported-brightgreen)

https://github.com/user-attachments/assets/demo-placeholder

## Features

- **One-click profile transcription** — username in, full text out
- **Whisper Large-v3** with SDPA (Scaled Dot-Product Attention) — no Flash Attention dependency
- **Hardware-aware inference** — auto-detects CUDA / Apple Silicon (MPS) / CPU, sets optimal dtype and batch size
- **No login required** — scrapes public profiles via headless Playwright
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

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │              Gradio Web UI                  │
                         │         (app.py — build_ui)                 │
                         └──────┬──────────────────┬──────────────────┘
                                │                  │
                    ┌───────────▼──────┐   ┌───────▼───────┐
                    │ process_profile  │   │ process_files │
                    └───────┬──────────┘   └───────┬───────┘
                            │                      │
               ┌────────────▼────────────┐         │
               │     scraper.py          │         │
               │                         │         │
               │  Playwright (headless)  │         │
               │  ┌───────────────────┐  │         │
               │  │ 1. List posts     │  │         │
               │  │    (pagination)   │  │         │
               │  ├───────────────────┤  │         │
               │  │ 2. /api/convert   │  │         │
               │  │    → proxy URL    │  │         │
               │  ├───────────────────┤  │         │
               │  │ 3. Download .mp4  │  │         │
               │  │    via proxy CDN  │  │         │
               │  └───────────────────┘  │         │
               └────────────┬────────────┘         │
                            │                      │
                            ▼                      ▼
               ┌─────────────────────────────────────────┐
               │           transcriber.py                 │
               │                                         │
               │  ffmpeg         Whisper Large-v3        │
               │  ┌──────┐      ┌────────────────────┐  │
               │  │ .mp4 ├─────►│ 30s chunks         │  │
               │  │  →   │      │ × batch_size       │  │
               │  │ .wav │      │ → SDPA attention    │  │
               │  └──────┘      │ → timestamps        │  │
               │                └────────────────────┘  │
               └──────────────────┬──────────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────────┐
               │           formatter.py                   │
               │                                         │
               │  Markdown  ·  JSON  ·  TXT              │
               └─────────────────────────────────────────┘

Hardware abstraction (device.py):
  CUDA  →  float16, batch 16–24, torch.cuda.empty_cache()
  MPS   →  float32, batch 8,     torch.mps.empty_cache()
  CPU   →  float32, batch 4
```

## Quick start

```bash
git clone https://github.com/aytzey/reels-transcriber.git
cd reels-transcriber

pip install -r requirements.txt
playwright install chromium

python app.py
```

Open **http://localhost:7860**.

The model (~3 GB) downloads automatically on first run.

### Platform-specific setup

**macOS (Apple Silicon)**
```bash
pip install -r requirements.txt       # MPS support ships with PyTorch
playwright install chromium
```

**Linux / Windows (NVIDIA GPU)**
```bash
# Install PyTorch with CUDA first — https://pytorch.org
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
playwright install chromium
```

**CPU-only**
```bash
pip install -r requirements.txt
playwright install chromium
```

## Project structure

```
├── app.py                          # Gradio UI + pipeline orchestration
├── reels_transcriber/
│   ├── device.py                   # Hardware detection (CUDA / MPS / CPU)
│   ├── transcriber.py              # Whisper pipeline, audio extraction, batched inference
│   ├── scraper.py                  # Headless Playwright Instagram scraper + proxy CDN download
│   └── formatter.py                # Markdown / JSON / TXT export
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

## How it works

**Scraping** — Playwright drives a headless Chromium browser to a third-party service. It intercepts the service's API responses to extract the post list (with cursor-based pagination) and signed proxy CDN URLs for each video. All downloads go through the proxy CDN (`media.igram.world`), which means the pipeline works even behind corporate firewalls that block `cdninstagram.com` directly.

**Transcription** — Each video is converted to 16 kHz mono WAV via ffmpeg. The Whisper pipeline splits audio into 30-second chunks and processes `batch_size` chunks in parallel. Attention uses PyTorch's native SDPA kernel (equivalent to Flash Attention 2, zero external deps). Device, dtype, and batch size are resolved once at startup by `device.py`.

**Why float32 on MPS?** — Whisper's cross-attention layers can produce NaN with float16 on Apple's MPS backend in PyTorch ≤2.3. Using float32 is ~1.5x slower but guarantees correct output. CUDA doesn't have this issue.

## Requirements

| Dependency | Purpose |
|---|---|
| `torch` + `torchaudio` | Model inference engine |
| `transformers` | Whisper pipeline |
| `gradio` | Web interface |
| `playwright` | Headless browser for scraping |
| `ffmpeg` (system) | Audio extraction from video |

## License

MIT
