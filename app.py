"""
Reels Transcriber — Gradio web application.

Four input modes:
1. Single URL — one Instagram Reel or TikTok video
2. Instagram Profile — all public reels from a username
3. TikTok Profile — all public videos from a username
4. Upload Videos — drag-and-drop local files
"""

from __future__ import annotations

import logging
import tempfile
import time
import traceback
from pathlib import Path

import gradio as gr

from reels_transcriber.device import DEVICE, DTYPE, BATCH_SIZE, device_summary
from reels_transcriber.transcriber import (
    load_model, transcribe, MODEL_NAME, MODEL_DISTIL, MODEL_LARGE,
)
from reels_transcriber.formatter import format_results

_log = logging.getLogger("reels_transcriber.app")

OUTPUT_DIR = Path(tempfile.gettempdir()) / "reels_transcriber"
OUTPUT_DIR.mkdir(exist_ok=True)

_MODEL_SHORT = MODEL_NAME.split("/")[-1]
_DEVICE_LABEL = device_summary(DEVICE)

_EMPTY_OUTPUTS = ("", None, None, "")


# ---------------------------------------------------------------------------
# Pipelines — each wrapped with robust error handling
# ---------------------------------------------------------------------------

def _resolve_model(model_choice: str) -> str:
    return MODEL_LARGE if model_choice == "large-v3 (accurate)" else MODEL_DISTIL


def process_ig_profile(username: str, language: str, model: str, progress=gr.Progress()):
    username = username.strip().lstrip("@").split("/")[-1].split("?")[0].strip()
    if not username:
        raise gr.Error("Please enter an Instagram username.")

    try:
        from reels_transcriber.scraper import scrape_and_download

        video_infos, user_info = scrape_and_download(
            username, OUTPUT_DIR / f"ig_{username}", progress
        )
    except Exception as exc:
        _log.error("IG scrape failed: %s\n%s", exc, traceback.format_exc())
        raise gr.Error(
            f"Failed to fetch @{username}'s profile. "
            "The service may be temporarily unavailable — please try again."
        )

    if not video_infos:
        raise gr.Error(
            f"No reels found for @{username}. "
            "The profile may be private, or no video reels are available."
        )

    model_name = _resolve_model(model)
    progress(0.6, desc=f"{len(video_infos)} reels downloaded, transcribing...")

    t0 = time.monotonic()
    results = transcribe(video_infos, language, progress, 0.6, 0.95, model_name=model_name)
    elapsed = time.monotonic() - t0

    display = f"@{username}"
    if user_info and user_info.get("full_name"):
        display = f"{user_info['full_name']} (@{username})"

    md, jp, tp = format_results(results, f"{display} - Reels Transcripts", OUTPUT_DIR)
    stats = _build_stats(len(results), elapsed, model_name)
    return md, jp, tp, stats


def process_tt_profile(username: str, language: str, model: str, progress=gr.Progress()):
    username = username.strip().lstrip("@").split("/")[-1].split("?")[0].strip()
    if not username:
        raise gr.Error("Please enter a TikTok username.")

    try:
        from reels_transcriber.tiktok import scrape_profile_videos

        video_infos, user_info = scrape_profile_videos(
            username, OUTPUT_DIR / f"tt_{username}", progress
        )
    except Exception as exc:
        _log.error("TT scrape failed: %s\n%s", exc, traceback.format_exc())
        raise gr.Error(
            f"Failed to fetch @{username}'s profile. "
            "The service may be temporarily unavailable — please try again."
        )

    if not video_infos:
        raise gr.Error(
            f"No videos found for @{username}. "
            "The profile may be private, or Cloudflare blocked the request. "
            "Try the Single URL tab instead."
        )

    model_name = _resolve_model(model)
    progress(0.6, desc=f"{len(video_infos)} videos downloaded, transcribing...")

    t0 = time.monotonic()
    results = transcribe(video_infos, language, progress, 0.6, 0.95, model_name=model_name)
    elapsed = time.monotonic() - t0

    display = f"@{username}"
    if user_info:
        nickname = (user_info.get("user") or {}).get("nickname", "")
        if nickname:
            display = f"{nickname} (@{username})"

    md, jp, tp = format_results(
        results, f"{display} - TikTok Transcripts", OUTPUT_DIR
    )
    stats = _build_stats(len(results), elapsed, model_name)
    return md, jp, tp, stats


def process_single_url(url: str, language: str, model: str, progress=gr.Progress()):
    url = url.strip()
    if not url:
        raise gr.Error("Please enter a URL.")
    if "tiktok.com" not in url and "instagram.com" not in url:
        raise gr.Error("Unsupported URL. Paste an Instagram Reel or TikTok video link.")

    progress(0, desc="Downloading video...")

    try:
        if "tiktok.com" in url:
            from reels_transcriber.tiktok import download_single_video
            info = download_single_video(url, OUTPUT_DIR / "single")
            platform = "TikTok"
        else:
            from reels_transcriber.scraper import download_single_reel
            info = download_single_reel(url, OUTPUT_DIR / "single")
            platform = "Instagram"
    except Exception as exc:
        _log.error("Download failed: %s\n%s", exc, traceback.format_exc())
        raise gr.Error("Download failed — the service may be temporarily unavailable.")

    if not info:
        raise gr.Error(
            f"Could not download this {platform} video. "
            "The link may be invalid, private, or the service is down."
        )

    model_name = _resolve_model(model)
    progress(0.4, desc="Transcribing...")

    t0 = time.monotonic()
    results = transcribe([info], language, progress, 0.4, 0.95, model_name=model_name)
    elapsed = time.monotonic() - t0

    md, jp, tp = format_results(results, f"{platform} Video Transcript", OUTPUT_DIR)
    stats = _build_stats(1, elapsed, model_name)
    return md, jp, tp, stats


def process_files(files, language: str, model: str, progress=gr.Progress()):
    if not files:
        raise gr.Error("Please upload at least one file.")

    file_infos = [
        {
            "path": f if isinstance(f, str) else f.name,
            "filename": Path(f if isinstance(f, str) else f.name).stem,
        }
        for f in files
    ]

    model_name = _resolve_model(model)

    t0 = time.monotonic()
    results = transcribe(file_infos, language, progress, model_name=model_name)
    elapsed = time.monotonic() - t0

    md, jp, tp = format_results(results, "Video Transcripts", OUTPUT_DIR)
    stats = _build_stats(len(results), elapsed, model_name)
    return md, jp, tp, stats


def _build_stats(count: int, elapsed: float, model_name: str) -> str:
    """Build a status line with performance stats."""
    avg = elapsed / count if count else 0
    model_short = model_name.split("/")[-1]
    return (
        f"**{count}** video{'s' if count != 1 else ''} transcribed in "
        f"**{elapsed:.1f}s** ({avg:.1f}s/file) "
        f"using {model_short} on {_DEVICE_LABEL}"
    )


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

LANGUAGES = [
    ("Auto-detect", "auto"), ("Turkish", "tr"), ("English", "en"),
    ("German", "de"), ("French", "fr"), ("Spanish", "es"),
    ("Arabic", "ar"), ("Russian", "ru"), ("Japanese", "ja"),
    ("Korean", "ko"), ("Chinese", "zh"), ("Portuguese", "pt"),
    ("Italian", "it"), ("Dutch", "nl"), ("Hindi", "hi"),
]

AUDIO_TYPES = [
    "video", "audio",
    ".mp4", ".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac",
]

CSS = """
/* ── Reset & base ─────────────────────────────────────── */
footer { display: none !important; }
.gradio-container { max-width: 960px !important; margin: auto; }

/* ── Header ───────────────────────────────────────────── */
.app-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.app-header h1 {
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #ec4899, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
}
.app-header .subtitle {
    color: var(--body-text-color-subdued);
    font-size: 1rem;
    line-height: 1.6;
}

/* ── Device badge ─────────────────────────────────────── */
.device-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 0.75rem;
    padding: 5px 14px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-accent);
    color: var(--body-text-color);
}
.device-badge .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 6px #22c55eaa;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ── Status bar ───────────────────────────────────────── */
.status-bar {
    text-align: center;
    padding: 0.6rem 1rem;
    font-size: 1rem;
}
.status-bar p { margin: 0; }

/* ── Transcript output ────────────────────────────────── */
.transcript-output { min-height: 200px; }

/* ── Footer ───────────────────────────────────────────── */
.app-footer {
    text-align: center;
    color: var(--body-text-color-subdued);
    font-size: 0.78rem;
    padding: 1.5rem 0 0.5rem;
    border-top: 1px solid var(--border-color-primary);
    margin-top: 1rem;
}
.app-footer a {
    color: #8b5cf6;
    text-decoration: none;
}
.app-footer a:hover { text-decoration: underline; }

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 640px) {
    .app-header h1 { font-size: 1.8rem; }
    .app-header .subtitle { font-size: 0.85rem; }
    .gradio-container { padding: 0 0.5rem !important; }
}
"""

MODELS = [
    ("distil-large-v3 (fast)", "distil-large-v3 (fast)"),
    ("large-v3 (accurate)", "large-v3 (accurate)"),
]


def _lang_dropdown() -> gr.Dropdown:
    return gr.Dropdown(label="Language", choices=LANGUAGES, value="auto")


def _model_dropdown() -> gr.Dropdown:
    return gr.Dropdown(label="Model", choices=MODELS, value="distil-large-v3 (fast)")


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Reels Transcriber") as demo:

        # ── Header ──────────────────────────────────────
        gr.HTML(f"""
        <div class="app-header">
            <h1>Reels Transcriber</h1>
            <p class="subtitle">
                Transcribe Instagram Reels & TikTok videos<br>
                with GPU-accelerated Whisper inference
            </p>
            <div class="device-badge">
                <span class="dot"></span>
                {_DEVICE_LABEL} &middot; batch={BATCH_SIZE}
            </div>
        </div>
        """)

        # ── Input ───────────────────────────────────────
        with gr.Tabs():

            # 1. Single URL
            with gr.TabItem("Single URL"):
                gr.Markdown(
                    "Paste an **Instagram Reel** or **TikTok video** URL."
                )
                with gr.Row():
                    with gr.Column(scale=4):
                        inp_url = gr.Textbox(
                            label="Video URL",
                            placeholder="https://www.instagram.com/reel/...  or  https://vm.tiktok.com/...",
                            lines=1,
                        )
                    with gr.Column(scale=1, min_width=140):
                        lang_url = _lang_dropdown()
                        model_url = _model_dropdown()
                btn_url = gr.Button("Transcribe", variant="primary", size="lg")

            # 2. Instagram Profile
            with gr.TabItem("Instagram Profile"):
                gr.Markdown(
                    "Enter a username to download and transcribe **all public reels**."
                )
                with gr.Row():
                    with gr.Column(scale=4):
                        inp_ig = gr.Textbox(
                            label="Username",
                            placeholder="vince.quant",
                            lines=1,
                        )
                    with gr.Column(scale=1, min_width=140):
                        lang_ig = _lang_dropdown()
                        model_ig = _model_dropdown()
                btn_ig = gr.Button(
                    "Fetch & Transcribe", variant="primary", size="lg"
                )

            # 3. TikTok Profile
            with gr.TabItem("TikTok Profile"):
                gr.Markdown(
                    "Enter a username to download and transcribe **all public videos**."
                )
                with gr.Row():
                    with gr.Column(scale=4):
                        inp_tt = gr.Textbox(
                            label="Username",
                            placeholder="khaby.lame",
                            lines=1,
                        )
                    with gr.Column(scale=1, min_width=140):
                        lang_tt = _lang_dropdown()
                        model_tt = _model_dropdown()
                btn_tt = gr.Button(
                    "Fetch & Transcribe", variant="primary", size="lg"
                )

            # 4. Upload Files
            with gr.TabItem("Upload Files"):
                gr.Markdown(
                    "Drag & drop **video or audio files** for batch transcription."
                )
                with gr.Row():
                    with gr.Column(scale=4):
                        inp_files = gr.File(
                            label="Video / Audio files",
                            file_count="multiple",
                            file_types=AUDIO_TYPES,
                            height=180,
                        )
                    with gr.Column(scale=1, min_width=140):
                        lang_f = _lang_dropdown()
                        model_f = _model_dropdown()
                btn_f = gr.Button("Transcribe", variant="primary", size="lg")

        # ── Status ──────────────────────────────────────
        status = gr.Markdown(elem_classes=["status-bar"])

        # ── Output ──────────────────────────────────────
        with gr.Tabs():
            with gr.TabItem("Transcripts"):
                out_md = gr.Markdown(elem_classes=["transcript-output"])
            with gr.TabItem("Export"):
                with gr.Row():
                    out_json = gr.File(label="JSON")
                    out_txt = gr.File(label="TXT")

        # ── Wiring ──────────────────────────────────────
        outputs = [out_md, out_json, out_txt, status]
        btn_url.click(process_single_url, [inp_url, lang_url, model_url], outputs)
        btn_ig.click(process_ig_profile, [inp_ig, lang_ig, model_ig], outputs)
        btn_tt.click(process_tt_profile, [inp_tt, lang_tt, model_tt], outputs)
        btn_f.click(process_files, [inp_files, lang_f, model_f], outputs)

        # ── Footer ──────────────────────────────────────
        gr.HTML(f"""
        <div class="app-footer">
            Insanely-Fast Whisper &middot; {_DEVICE_LABEL} &middot; batch={BATCH_SIZE}
            <br>
            <a href="https://github.com/aytzey/reels-transcriber"
               target="_blank">github.com/aytzey/reels-transcriber</a>
        </div>
        """)

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"Device : {_DEVICE_LABEL}")
    print(f"Dtype  : {DTYPE}")
    print(f"Batch  : {BATCH_SIZE}")
    print(f"Model  : {MODEL_NAME}")
    print()
    print("Loading model (first run downloads ~3 GB)...")
    load_model()
    print("Model ready.\n")

    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="pink",
            neutral_hue="slate",
            font=("Inter", "system-ui", "sans-serif"),
        ),
        css=CSS,
    )


if __name__ == "__main__":
    main()
