# StoryToText

Editorial-style transcription workspace for YouTube, TikTok, Instagram Reels, uploaded media, and API-driven jobs.

This repo now ships a local SaaS-style product shell inspired by the `tasks/stitch_new_transcription` references:

- Public landing page
- 3-step onboarding
- Dashboard, New Transcription, History, Transcript Detail
- Billing, Settings, API Keys, Developer Docs
- Background transcription jobs with web + API entry points
- Local persistent workspace state in `runtime_data/state.json`

The actual transcription pipeline still uses the existing Whisper-based backend modules in `reels_transcriber/`.

## What Changed

The old single-page Gradio UI has been replaced with a lightweight web app server and a custom frontend shell that matches the premium StoryToText direction from `tasks/`.

Key additions:

- Real route-based app shell instead of one tabbed tool screen
- Local job queue and archive history
- Copy-once API key management
- REST API endpoints for external automation
- YouTube single-video and collection support via `yt-dlp`
- Persistent user settings, onboarding state, billing metrics, and job records

## Quick Start

```bash
git clone https://github.com/aytzey/reels-transcriber.git
cd reels-transcriber

pip install -r requirements.txt
playwright install chromium

python3 app.py
```

Open `http://127.0.0.1:7860`.

Notes:

- The shell itself runs on the Python standard library server and starts without Gradio.
- Actual transcription jobs still require the heavy runtime dependencies from `requirements.txt`.
- `ffmpeg` must be installed on the host system.
- Local app state is written under `runtime_data/`.

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
├── app.py
├── web/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── reels_transcriber/
│   ├── jobs.py
│   ├── state.py
│   ├── youtube.py
│   ├── transcriber.py
│   ├── scraper.py
│   ├── tiktok.py
│   └── formatter.py
├── runtime_data/        # generated at runtime, ignored by git
└── tasks/
    └── stitch_new_transcription/
```

## Existing Backend Modules

- `reels_transcriber/transcriber.py`: Whisper transcription pipeline
- `reels_transcriber/scraper.py`: Instagram single + profile download
- `reels_transcriber/tiktok.py`: TikTok single + profile download
- `reels_transcriber/youtube.py`: YouTube single + collection download
- `reels_transcriber/jobs.py`: job execution and status transitions
- `reels_transcriber/state.py`: local persistent workspace state

## Runtime Caveats

- If dependencies such as `torch`, `transformers`, or `playwright` are missing, the shell still loads but transcription jobs fail gracefully with an install message.
- Uploaded media and generated exports are stored locally under `runtime_data/`.
- The local API surface is intended for single-user/local workflows, not hardened multi-tenant production.

## License

MIT
