"""
Reels Transcriber — Gradio web application.

Four modes:
1. Instagram Profile — all public reels from a username
2. TikTok Profile — all public videos from a username
3. Single URL — one Instagram Reel or TikTok video
4. Upload Videos — drag-and-drop local files
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import gradio as gr

from reels_transcriber.device import DEVICE, DTYPE, BATCH_SIZE, device_summary
from reels_transcriber.transcriber import load_model, transcribe, MODEL_NAME
from reels_transcriber.formatter import format_results

OUTPUT_DIR = Path(tempfile.gettempdir()) / "reels_transcriber"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Pipeline: Instagram profile
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
    return md, jp, tp, f"**{len(results)}** reels transcribed!"


# ---------------------------------------------------------------------------
# Pipeline: TikTok profile
# ---------------------------------------------------------------------------

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
    return md, jp, tp, f"**{len(results)}** TikTok videos transcribed!"


# ---------------------------------------------------------------------------
# Pipeline: Single URL (Instagram Reel or TikTok video)
# ---------------------------------------------------------------------------

def _is_tiktok(url: str) -> bool:
    return "tiktok.com" in url or "vm.tiktok.com" in url


def _is_instagram(url: str) -> bool:
    return "instagram.com" in url


def process_single_url(url: str, language: str, progress=gr.Progress()):
    url = url.strip()
    if not url:
        raise gr.Error("Please enter a URL.")

    progress(0, desc="Downloading video...")

    if _is_tiktok(url):
        from reels_transcriber.tiktok import download_single_video

        info = download_single_video(url, OUTPUT_DIR / "single")
        if not info:
            raise gr.Error("Could not download this TikTok video. Check the URL.")
        platform = "TikTok"

    elif _is_instagram(url):
        from reels_transcriber.scraper import download_single_reel

        info = download_single_reel(url, OUTPUT_DIR / "single")
        if not info:
            raise gr.Error("Could not download this Instagram Reel. Check the URL.")
        platform = "Instagram"

    else:
        raise gr.Error(
            "Unsupported URL. Please paste an Instagram Reel or TikTok video link."
        )

    progress(0.4, desc="Transcribing...")
    results = transcribe([info], language, progress, 0.4, 0.95)

    md, jp, tp = format_results(
        results, f"{platform} Video Transcript", OUTPUT_DIR
    )
    return md, jp, tp, f"**1** {platform} video transcribed!"


# ---------------------------------------------------------------------------
# Pipeline: Local file upload
# ---------------------------------------------------------------------------

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
    return md, jp, tp, f"**{len(results)}** videos transcribed!"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

CSS = """
.header { text-align: center; margin-bottom: .5rem }
.header h1 {
    font-size: 2.2rem;
    background: linear-gradient(135deg, #e91e8c, #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.header p { color: #888; font-size: 1.05rem }
.stat { text-align: center; padding: .8rem; font-size: 1.15rem }
footer { display: none !important }
"""

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


def _lang_dropdown(label: str = "Language") -> gr.Dropdown:
    return gr.Dropdown(label=label, choices=LANGUAGES, value="auto")


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Reels Transcriber") as demo:
        gr.HTML(
            '<div class="header">'
            "<h1>Reels Transcriber</h1>"
            "<p>Transcribe Instagram Reels & TikTok videos with "
            f"<b>{MODEL_NAME.split('/')[-1]}</b> on "
            f"{device_summary(DEVICE)}.</p></div>"
        )

        # -- Shared outputs (defined first, wired later) --
        status = gr.Markdown(elem_classes=["stat"], visible=False)
        with gr.Tabs():
            with gr.TabItem("Transcripts"):
                out_md = gr.Markdown()
            with gr.TabItem("Download"):
                with gr.Row():
                    out_json = gr.File(label="JSON")
                    out_txt = gr.File(label="TXT")

        outputs = [out_md, out_json, out_txt, status]

        # -- Input tabs --
        with gr.Tabs():
            # --- 1. Single URL ---
            with gr.TabItem("Single URL"):
                gr.Markdown(
                    "*Paste an Instagram Reel or TikTok video URL.*"
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        inp_url = gr.Textbox(
                            label="Video URL",
                            placeholder="https://www.instagram.com/reel/ABC123/  or  https://vm.tiktok.com/ZMr...",
                            info="Supports Instagram Reels and TikTok videos",
                        )
                    with gr.Column(scale=1):
                        lang_url = _lang_dropdown()
                btn_url = gr.Button("Transcribe", variant="primary", size="lg")

            # --- 2. Instagram Profile ---
            with gr.TabItem("Instagram Profile"):
                gr.Markdown(
                    "*Enter a username — all public reels will be "
                    "downloaded and transcribed.*"
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        inp_ig = gr.Textbox(
                            label="Username",
                            placeholder="vince.quant",
                            info="Without @ or paste the profile URL",
                        )
                    with gr.Column(scale=1):
                        lang_ig = _lang_dropdown()
                btn_ig = gr.Button(
                    "Fetch & Transcribe Reels", variant="primary", size="lg"
                )

            # --- 3. TikTok Profile ---
            with gr.TabItem("TikTok Profile"):
                gr.Markdown(
                    "*Enter a TikTok username — all public videos will be "
                    "downloaded and transcribed.*"
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        inp_tt = gr.Textbox(
                            label="Username",
                            placeholder="khaby.lame",
                            info="Without @ or paste the profile URL",
                        )
                    with gr.Column(scale=1):
                        lang_tt = _lang_dropdown()
                btn_tt = gr.Button(
                    "Fetch & Transcribe Videos", variant="primary", size="lg"
                )

            # --- 4. Upload Files ---
            with gr.TabItem("Upload Videos"):
                gr.Markdown(
                    "*Drag & drop video or audio files for batch transcription.*"
                )
                with gr.Row():
                    with gr.Column(scale=3):
                        inp_files = gr.File(
                            label="Video / Audio files",
                            file_count="multiple",
                            file_types=AUDIO_TYPES,
                            height=200,
                        )
                    with gr.Column(scale=1):
                        lang_f = _lang_dropdown()
                btn_f = gr.Button("Transcribe", variant="primary", size="lg")

        # -- Wire buttons to pipelines --
        btn_url.click(process_single_url, [inp_url, lang_url], outputs)
        btn_ig.click(process_ig_profile, [inp_ig, lang_ig], outputs)
        btn_tt.click(process_tt_profile, [inp_tt, lang_tt], outputs)
        btn_f.click(process_files, [inp_files, lang_f], outputs)

        gr.HTML(
            '<div style="text-align:center;color:#666;margin-top:1.5rem;'
            'font-size:.85rem">openai/whisper-large-v3 &bull; GPU accelerated</div>'
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"Device : {device_summary(DEVICE)}")
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
            primary_hue="pink",
            secondary_hue="purple",
            neutral_hue="slate",
        ),
        css=CSS,
    )


if __name__ == "__main__":
    main()
