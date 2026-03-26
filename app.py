"""
Reels Transcriber — Gradio web application.

Four input modes:
1. Single URL — one Instagram Reel or TikTok video
2. Instagram Profile — all public reels from a username
3. TikTok Profile — all public videos from a username
4. Upload Videos — drag-and-drop local files
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import gradio as gr

from reels_transcriber.device import DEVICE, DTYPE, BATCH_SIZE, device_summary
from reels_transcriber.transcriber import load_model, transcribe, MODEL_NAME
from reels_transcriber.formatter import format_results

OUTPUT_DIR = Path(tempfile.gettempdir()) / "reels_transcriber"
OUTPUT_DIR.mkdir(exist_ok=True)

_MODEL_SHORT = MODEL_NAME.split("/")[-1]
_DEVICE_LABEL = device_summary(DEVICE)


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

def process_ig_profile(username: str, language: str, progress=gr.Progress()):
    from reels_transcriber.scraper import scrape_and_download

    username = username.strip().lstrip("@").split("/")[-1].split("?")[0].strip()
    if not username:
        raise gr.Error("Please enter an Instagram username.")

    video_infos, user_info = scrape_and_download(
        username, OUTPUT_DIR / f"ig_{username}", progress
    )
    if not video_infos:
        raise gr.Error("No reels could be downloaded.")

    progress(0.6, desc=f"{len(video_infos)} reels downloaded, transcribing...")
    results = transcribe(video_infos, language, progress, 0.6, 0.95)

    display = f"@{username}"
    if user_info and user_info.get("full_name"):
        display = f"{user_info['full_name']} (@{username})"

    md, jp, tp = format_results(results, f"{display} - Reels Transcripts", OUTPUT_DIR)
    return md, jp, tp, f"**{len(results)}** reels transcribed successfully."


def process_tt_profile(username: str, language: str, progress=gr.Progress()):
    from reels_transcriber.tiktok import scrape_profile_videos

    username = username.strip().lstrip("@").split("/")[-1].split("?")[0].strip()
    if not username:
        raise gr.Error("Please enter a TikTok username.")

    video_infos, user_info = scrape_profile_videos(
        username, OUTPUT_DIR / f"tt_{username}", progress
    )
    if not video_infos:
        raise gr.Error(
            f"No videos found for @{username}. "
            "The profile may be private, or Cloudflare blocked the request. "
            "Try the Single URL tab instead."
        )

    progress(0.6, desc=f"{len(video_infos)} videos downloaded, transcribing...")
    results = transcribe(video_infos, language, progress, 0.6, 0.95)

    display = f"@{username}"
    if user_info:
        nickname = user_info.get("user", {}).get("nickname", "")
        if nickname:
            display = f"{nickname} (@{username})"

    md, jp, tp = format_results(
        results, f"{display} - TikTok Transcripts", OUTPUT_DIR
    )
    return md, jp, tp, f"**{len(results)}** TikTok videos transcribed successfully."


def process_single_url(url: str, language: str, progress=gr.Progress()):
    url = url.strip()
    if not url:
        raise gr.Error("Please enter a URL.")

    progress(0, desc="Downloading video...")

    if "tiktok.com" in url:
        from reels_transcriber.tiktok import download_single_video
        info = download_single_video(url, OUTPUT_DIR / "single")
        if not info:
            raise gr.Error("Could not download this TikTok video.")
        platform = "TikTok"
    elif "instagram.com" in url:
        from reels_transcriber.scraper import download_single_reel
        info = download_single_reel(url, OUTPUT_DIR / "single")
        if not info:
            raise gr.Error("Could not download this Instagram Reel.")
        platform = "Instagram"
    else:
        raise gr.Error("Unsupported URL. Paste an Instagram Reel or TikTok video link.")

    progress(0.4, desc="Transcribing...")
    results = transcribe([info], language, progress, 0.4, 0.95)

    md, jp, tp = format_results(results, f"{platform} Video Transcript", OUTPUT_DIR)
    return md, jp, tp, f"**1** {platform} video transcribed successfully."


def process_files(files, language: str, progress=gr.Progress()):
    if not files:
        raise gr.Error("Please upload at least one file.")

    file_infos = [
        {
            "path": f if isinstance(f, str) else f.name,
            "filename": Path(f if isinstance(f, str) else f.name).stem,
        }
        for f in files
    ]

    results = transcribe(file_infos, language, progress)
    md, jp, tp = format_results(results, "Video Transcripts", OUTPUT_DIR)
    return md, jp, tp, f"**{len(results)}** videos transcribed successfully."


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
footer { display: none !important }

/* ── Header ───────────────────────────────────────────── */
.app-header {
    text-align: center;
    padding: 2rem 1rem 1rem;
}
.app-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ec4899, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.35rem;
}
.app-header .subtitle {
    color: #6b7280;
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
    background: linear-gradient(135deg, #f0abfc22, #c084fc22);
    border: 1px solid #c084fc44;
    color: #7c3aed;
}
.device-badge .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 6px #22c55eaa;
}

/* ── Status bar ───────────────────────────────────────── */
.status-bar {
    text-align: center;
    padding: 0.6rem 1rem;
    font-size: 1.05rem;
}
.status-bar p { margin: 0; }

/* ── Footer ───────────────────────────────────────────── */
.app-footer {
    text-align: center;
    color: #9ca3af;
    font-size: 0.78rem;
    padding: 1.5rem 0 0.5rem;
    border-top: 1px solid #e5e7eb22;
    margin-top: 1rem;
}
.app-footer a { color: #8b5cf6; text-decoration: none; }
"""


def _lang_dropdown() -> gr.Dropdown:
    return gr.Dropdown(label="Language", choices=LANGUAGES, value="auto")


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Reels Transcriber") as demo:

        # ── Header ──────────────────────────────────────
        gr.HTML(f"""
        <div class="app-header">
            <h1>Reels Transcriber</h1>
            <p class="subtitle">
                Transcribe Instagram Reels and TikTok videos<br>
                using <strong>{_MODEL_SHORT}</strong> with GPU-accelerated inference.
            </p>
            <div class="device-badge">
                <span class="dot"></span>
                {_DEVICE_LABEL}
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
                btn_f = gr.Button("Transcribe", variant="primary", size="lg")

        # ── Status ──────────────────────────────────────
        status = gr.Markdown(elem_classes=["status-bar"])

        # ── Output ──────────────────────────────────────
        with gr.Tabs():
            with gr.TabItem("Transcripts"):
                out_md = gr.Markdown()
            with gr.TabItem("Export"):
                with gr.Row():
                    out_json = gr.File(label="JSON")
                    out_txt = gr.File(label="TXT")

        # ── Wiring ──────────────────────────────────────
        outputs = [out_md, out_json, out_txt, status]
        btn_url.click(process_single_url, [inp_url, lang_url], outputs)
        btn_ig.click(process_ig_profile, [inp_ig, lang_ig], outputs)
        btn_tt.click(process_tt_profile, [inp_tt, lang_tt], outputs)
        btn_f.click(process_files, [inp_files, lang_f], outputs)

        # ── Footer ──────────────────────────────────────
        gr.HTML(f"""
        <div class="app-footer">
            {_MODEL_SHORT} &middot; SDPA Attention &middot; {_DEVICE_LABEL}
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
