"""Reels Transcriber -- Gradio web UI."""

import tempfile
from pathlib import Path

import gradio as gr

from reels_transcriber.device import DEVICE, DTYPE, BATCH_SIZE
from reels_transcriber.transcriber import get_pipeline, MODEL_NAME
from reels_transcriber.scraper import scrape_and_download
from reels_transcriber.formatter import format_results

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "reels_transcriber"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# -- pipelines ---------------------------------------------------------------

def process_profile(username: str, language: str, progress=gr.Progress()):
    username = username.strip().lstrip("@").split("/")[-1].split("?")[0].strip()
    if not username:
        raise gr.Error("Please enter an Instagram username.")

    video_infos, user_info = scrape_and_download(
        username, DOWNLOAD_DIR / username, progress
    )
    if not video_infos:
        raise gr.Error("No videos could be downloaded.")

    progress(0.6, desc=f"{len(video_infos)} reels downloaded, transcribing...")

    from reels_transcriber.transcriber import transcribe

    results = transcribe(
        video_infos, language, progress, progress_start=0.6, progress_end=0.95
    )

    display = f"@{username}"
    if user_info and user_info.get("full_name"):
        display = f"{user_info['full_name']} (@{username})"

    md, jp, tp = format_results(
        results, f"{display} - Reels Transcripts", DOWNLOAD_DIR
    )
    return md, jp, tp, f"**{len(results)}** reels transcribed successfully!"


def process_files(files, language: str, progress=gr.Progress()):
    if not files:
        raise gr.Error("Please upload at least one video or audio file.")

    file_infos = [
        {"path": (f if isinstance(f, str) else f.name), "filename": Path(f if isinstance(f, str) else f.name).stem}
        for f in files
    ]

    from reels_transcriber.transcriber import transcribe

    results = transcribe(file_infos, language, progress)
    md, jp, tp = format_results(results, "Video Transcripts", DOWNLOAD_DIR)
    return md, jp, tp, f"**{len(results)}** videos transcribed successfully!"


# -- UI ----------------------------------------------------------------------

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

LANG_CHOICES = [
    ("Auto-detect", "auto"), ("Turkish", "tr"), ("English", "en"),
    ("German", "de"), ("French", "fr"), ("Spanish", "es"),
    ("Arabic", "ar"), ("Russian", "ru"), ("Japanese", "ja"), ("Korean", "ko"),
]

with gr.Blocks(title="Reels Transcriber") as demo:
    gr.HTML(
        '<div class="header">'
        "<h1>Reels Transcriber</h1>"
        "<p>Transcribe any public Instagram profile's Reels with "
        "<b>Whisper Large-v3</b> &mdash; GPU-accelerated.</p></div>"
    )

    with gr.Tabs():
        with gr.TabItem("Instagram Profile"):
            gr.Markdown(
                "*Enter a username. All public reels will be downloaded "
                "and transcribed automatically.*"
            )
            with gr.Row():
                with gr.Column(scale=3):
                    inp_user = gr.Textbox(
                        label="Username",
                        placeholder="vince.quant",
                        info="Without @ or paste the profile URL",
                    )
                with gr.Column(scale=1):
                    inp_lang_ig = gr.Dropdown(
                        label="Language", choices=LANG_CHOICES, value="auto"
                    )
            btn_ig = gr.Button(
                "Fetch & Transcribe Reels", variant="primary", size="lg"
            )

        with gr.TabItem("Upload Videos"):
            gr.Markdown("*Drag & drop video or audio files for batch transcription.*")
            with gr.Row():
                with gr.Column(scale=3):
                    inp_files = gr.File(
                        label="Video / Audio files",
                        file_count="multiple",
                        file_types=[
                            "video", "audio",
                            ".mp4", ".mp3", ".wav", ".m4a",
                            ".webm", ".ogg", ".flac",
                        ],
                        height=200,
                    )
                with gr.Column(scale=1):
                    inp_lang_f = gr.Dropdown(
                        label="Language", choices=LANG_CHOICES, value="auto"
                    )
            btn_f = gr.Button("Transcribe", variant="primary", size="lg")

    status = gr.Markdown(elem_classes=["stat"])
    with gr.Tabs():
        with gr.TabItem("Transcripts"):
            out_md = gr.Markdown()
        with gr.TabItem("Download"):
            with gr.Row():
                out_json = gr.File(label="JSON")
                out_txt = gr.File(label="TXT")

    btn_ig.click(
        process_profile,
        [inp_user, inp_lang_ig],
        [out_md, out_json, out_txt, status],
    )
    btn_f.click(
        process_files,
        [inp_files, inp_lang_f],
        [out_md, out_json, out_txt, status],
    )

    gr.HTML(
        '<div style="text-align:center;color:#666;margin-top:1.5rem;'
        'font-size:.85rem">openai/whisper-large-v3 &bull; GPU accelerated</div>'
    )


def main():
    print(f"Device: {DEVICE}  |  Dtype: {DTYPE}  |  Batch size: {BATCH_SIZE}")
    print("Loading Whisper Large-v3 model...")
    get_pipeline()
    print("Model ready! Starting server...")
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
