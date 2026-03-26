"""Whisper Large-v3 transcription engine."""

import os
import subprocess
import threading
from pathlib import Path
from typing import Callable

import torch
from transformers import pipeline

from .device import DEVICE, DTYPE, BATCH_SIZE, empty_cache

MODEL_NAME = "openai/whisper-large-v3"

_pipe = None
_lock = threading.Lock()


def get_pipeline():
    """Lazy-load the Whisper pipeline (first call downloads the model)."""
    global _pipe
    if _pipe is None:
        with _lock:
            if _pipe is None:
                _pipe = pipeline(
                    "automatic-speech-recognition",
                    model=MODEL_NAME,
                    torch_dtype=DTYPE,
                    device=DEVICE,
                    model_kwargs={"attn_implementation": "sdpa"},
                )
                empty_cache(DEVICE)
    return _pipe


def _extract_audio(video_path: str) -> str:
    """Convert video to 16 kHz mono WAV via ffmpeg."""
    wav = video_path.rsplit(".", 1)[0] + ".wav"
    if os.path.exists(wav):
        return wav
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn",
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav],
        capture_output=True,
        timeout=120,
    )
    return wav if os.path.exists(wav) else video_path


def transcribe(
    file_infos: list[dict],
    language: str = "auto",
    progress_cb: Callable | None = None,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
) -> list[dict]:
    """Transcribe a list of video/audio files.

    Each *file_infos* entry must contain at least ``{"path": "..."}`` and may
    include ``shortcode``, ``date``, ``caption``, ``url``, ``filename``.
    """
    pipe = get_pipeline()
    lang = None if language == "auto" else language

    generate_kwargs: dict = {"task": "transcribe"}
    if lang:
        generate_kwargs["language"] = lang

    results: list[dict] = []
    total = len(file_infos)

    for i, info in enumerate(file_infos):
        if progress_cb:
            pct = progress_start + (progress_end - progress_start) * (i / total)
            progress_cb(pct, desc=f"Transcribing ({i + 1}/{total})...")
        try:
            audio = _extract_audio(info["path"])
            out = pipe(
                audio,
                chunk_length_s=30,
                batch_size=BATCH_SIZE,
                generate_kwargs=generate_kwargs,
                return_timestamps=True,
            )
            text = out["text"].strip()
            chunks = out.get("chunks", [])
        except Exception as e:
            text = f"[ERROR: {e}]"
            chunks = []

        results.append({
            "filename": info.get("filename", Path(info["path"]).stem),
            "shortcode": info.get("shortcode", ""),
            "date": info.get("date", ""),
            "caption": info.get("caption", ""),
            "url": info.get("url", ""),
            "transcription": text,
            "chunks": [
                {"timestamp": c.get("timestamp"), "text": c.get("text", "")}
                for c in chunks
            ],
        })

    return results
