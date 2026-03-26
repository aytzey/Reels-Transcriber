"""
Whisper Large-v3 inference engine with hardware-aware batching.

Pipeline: video → ffmpeg audio extraction → chunked batched ASR → text

The HuggingFace ``transformers.pipeline`` handles Whisper's native chunked
long-form transcription: audio is split into 30-second segments, processed in
parallel batches on the GPU, and decoded with timestamps.  We configure SDPA
(Scaled Dot-Product Attention) as the attention backend — it's PyTorch-native
and works across CUDA, MPS, and CPU without external dependencies.

Batch size and dtype are selected at import time by ``device.py`` based on the
detected accelerator.
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Callable

from transformers import pipeline as hf_pipeline

from .device import DEVICE, DTYPE, BATCH_SIZE, empty_cache

MODEL_NAME = "openai/whisper-large-v3"

_pipe = None
_lock = threading.Lock()


def load_model():
    """Eagerly load the Whisper pipeline.  Safe to call multiple times."""
    global _pipe
    if _pipe is not None:
        return _pipe
    with _lock:
        if _pipe is None:
            _pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=MODEL_NAME,
                torch_dtype=DTYPE,
                device=DEVICE,
                model_kwargs={"attn_implementation": "sdpa"},
            )
            empty_cache(DEVICE)
    return _pipe


def _extract_audio(video_path: str) -> str:
    """Convert any media file to 16 kHz mono WAV via ffmpeg.

    Returns the wav path on success, or the original path as a fallback so
    the pipeline can still attempt decoding.
    """
    wav = video_path.rsplit(".", 1)[0] + ".wav"
    if os.path.exists(wav):
        return wav
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn",                  # drop video stream
            "-acodec", "pcm_s16le", # 16-bit PCM
            "-ar", "16000",         # 16 kHz (Whisper's native rate)
            "-ac", "1",             # mono
            wav,
        ],
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
    """Transcribe a batch of video/audio files.

    Parameters
    ----------
    file_infos:
        List of dicts, each with at least ``{"path": "/abs/path"}``.
        Optional keys: ``shortcode``, ``date``, ``caption``, ``url``, ``filename``.
    language:
        ISO 639-1 code (e.g. ``"en"``, ``"tr"``) or ``"auto"`` for detection.
    progress_cb:
        ``progress_cb(fraction, desc=...)`` for UI progress reporting.
    progress_start / progress_end:
        Map progress to a sub-range of [0, 1] when called as part of a
        larger pipeline.

    Returns
    -------
    List of result dicts with ``transcription``, ``chunks``, and all
    passthrough metadata from the input.
    """
    pipe = load_model()
    lang = None if language == "auto" else language

    generate_kwargs: dict = {"task": "transcribe"}
    if lang:
        generate_kwargs["language"] = lang

    results: list[dict] = []
    total = len(file_infos)
    t0 = __import__("time").monotonic()

    for i, info in enumerate(file_infos):
        if progress_cb:
            pct = progress_start + (progress_end - progress_start) * (i / total)
            elapsed = __import__("time").monotonic() - t0
            progress_cb(
                pct,
                desc=f"Transcribing {i + 1}/{total}  ({elapsed:.0f}s elapsed)",
            )

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
        except Exception as exc:
            text = f"[ERROR: {exc}]"
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
