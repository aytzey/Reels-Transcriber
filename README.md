# Reels Transcriber (StoryToText)

**Paste a Reel, TikTok, or YouTube link and get clean text in seconds — a local GPU-batched Whisper pipeline (distil/large-v3, Flash Attention, auto VRAM batching) with a web UI and REST API. No cloud required.**

Reels Transcriber is a local-first transcription workspace. A lightweight Python web app (StoryToText) sits on top of a batched Whisper backend and downloaders for Instagram Reels, TikTok, and YouTube. Everything — jobs, transcripts, API keys, settings — is stored on your machine under `runtime_data/`.

## Features

- **Web UI**: landing page, onboarding, dashboard, new-transcription flow, history, transcript detail, settings, and API key management
- **REST API**: submit jobs, poll status, and fetch results with a bearer API key
- **Sources**: Instagram Reels (single + profile), TikTok (single + profile), YouTube (single video + collections via `yt-dlp`), and direct media uploads
- **Fast inference**: HuggingFace ASR pipeline with Flash Attention 2 (or SDPA fallback), fp16 on CUDA, batch size auto-scaled from available VRAM, parallel ffmpeg audio extraction, and automatic OOM recovery with batch-size halving
- **Hardware-aware**: CUDA > Apple Silicon MPS > CPU, selected automatically
- **Models**: `distil-whisper/distil-large-v3` by default (fast); `openai/whisper-large-v3` optional per job

## Quick Start

```bash
git clone https://github.com/aytzey/Reels-Transcriber.git
cd Reels-Transcriber

pip install -r requirements.txt
playwright install chromium

python3 app.py
```

Open `http://127.0.0.1:7860`.

Notes:

- The web shell runs on the Python standard library HTTP server — no Gradio.
- Transcription jobs need the heavy runtime dependencies from `requirements.txt` (`torch`, `transformers`, etc.).
- `ffmpeg` must be installed on the host system.
- Local app state is written under `runtime_data/` (git-ignored).

## API Overview

Create a key from the in-app **API Keys** page, then use:

```bash
curl -X POST http://127.0.0.1:7860/api/v1/transcriptions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "single_url",
    "source_value": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "platform_hint": "youtube",
    "language": "en",
    "model": "distil-large-v3 (fast)"
  }'
```

Then poll:

```bash
curl http://127.0.0.1:7860/api/v1/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

And retrieve the result:

```bash
curl http://127.0.0.1:7860/api/v1/jobs/JOB_ID/result \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Project Structure

```text
├── app.py                  # HTTP server, routes, REST API
├── web/                    # frontend shell (index.html, styles.css, app.js)
├── reels_transcriber/
│   ├── transcriber.py      # batched Whisper pipeline (Flash Attention / SDPA, fp16)
│   ├── device.py           # CUDA/MPS/CPU detection, VRAM-based batch sizing
│   ├── scraper.py          # Instagram single + profile download
│   ├── tiktok.py           # TikTok single + profile download
│   ├── youtube.py          # YouTube single + collection download (yt-dlp)
│   ├── jobs.py             # job execution and status transitions
│   ├── state.py            # local persistent workspace state
│   └── formatter.py        # transcript formatting and exports
└── runtime_data/           # generated at runtime, ignored by git
```

## Runtime Caveats

- If dependencies such as `torch`, `transformers`, or `playwright` are missing, the shell still loads but transcription jobs fail with an install message.
- Uploaded media and generated exports are stored locally under `runtime_data/`.
- The local API surface is intended for single-user/local workflows, not hardened multi-tenant production.

## License

MIT
