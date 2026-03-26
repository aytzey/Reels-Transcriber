"""
Whisper Large-v3 inference engine with hardware-aware batching.

Pipeline: video -> parallel ffmpeg extraction -> chunked batched ASR -> text

Audio extraction runs in parallel across CPU cores before transcription
begins.  Whisper processes 30-second chunks in batches on the GPU.

Attention backend selection:
- Flash Attention 2 (if ``flash-attn`` is installed and CUDA sm_80+)
- SDPA fallback (PyTorch-native, works everywhere)
"""

from __future__ import annotations

# Suppress noisy per-file warnings BEFORE any transformers import.
import os as _os
import warnings as _w
import logging as _log

_os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

_w.filterwarnings("ignore", category=FutureWarning)
_w.filterwarnings("ignore", category=UserWarning, module="transformers")
_w.filterwarnings("ignore", message=".*chunk_length_s.*")
_w.filterwarnings("ignore", message=".*attention mask.*")
_w.filterwarnings("ignore", message=".*pipelines sequentially.*")
_log.getLogger("transformers").setLevel(_log.ERROR)

import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from transformers import pipeline as hf_pipeline

from .device import DEVICE, DTYPE, BATCH_SIZE, empty_cache

MODEL_NAME = "openai/whisper-large-v3"

_pipe = None
_lock = threading.Lock()


def _detect_attn_impl() -> str:
    """Pick the best available attention implementation."""
    if not DEVICE.startswith("cuda"):
        return "sdpa"
    try:
        import flash_attn  # noqa: F401
        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def load_model():
    """Eagerly load the Whisper pipeline.  Safe to call multiple times."""
    global _pipe
    if _pipe is not None:
        return _pipe
    with _lock:
        if _pipe is None:
            attn = _detect_attn_impl()
            _pipe = hf_pipeline(
                "automatic-speech-recognition",
                model=MODEL_NAME,
                torch_dtype=DTYPE,
                device=DEVICE,
                model_kwargs={"attn_implementation": attn},
            )
            empty_cache(DEVICE)
            print(f"  Attention: {attn}")
    return _pipe


# ---------------------------------------------------------------------------
# Audio extraction (parallelized)
# ---------------------------------------------------------------------------

def _extract_audio(video_path: str) -> str:
    """Convert any media file to 16 kHz mono WAV via ffmpeg."""
    wav = video_path.rsplit(".", 1)[0] + ".wav"
    if os.path.exists(wav):
        return wav
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-threads", "0",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            wav,
        ],
        capture_output=True,
        timeout=120,
    )
    return wav if os.path.exists(wav) else video_path


def _extract_all_audio(
    file_infos: list[dict],
    progress_cb: Callable | None,
    progress_start: float,
    progress_extract_end: float,
) -> list[str]:
    """Extract audio from all files in parallel using a thread pool."""
    paths = [info["path"] for info in file_infos]
    audio_paths: list[str | None] = [None] * len(paths)
    total = len(paths)

    if progress_cb:
        progress_cb(progress_start, desc=f"Extracting audio from {total} files...")

    with ThreadPoolExecutor(max_workers=min(4, total)) as pool:
        futures = {
            pool.submit(_extract_audio, p): idx for idx, p in enumerate(paths)
        }
        done = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                audio_paths[idx] = future.result()
            except Exception:
                audio_paths[idx] = paths[idx]
            done += 1
            if progress_cb:
                pct = progress_start + (progress_extract_end - progress_start) * (done / total)
                progress_cb(pct, desc=f"Extracting audio ({done}/{total})...")

    return [p or paths[i] for i, p in enumerate(audio_paths)]


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def transcribe(
    file_infos: list[dict],
    language: str = "auto",
    progress_cb: Callable | None = None,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
) -> list[dict]:
    """Transcribe a batch of video/audio files.

    1. Extract audio from all files in parallel (threaded ffmpeg).
    2. Run Whisper inference on GPU (each file chunked + batched internally).
    """
    pipe = load_model()
    lang = None if language == "auto" else language

    generate_kwargs: dict = {"task": "transcribe"}
    if lang:
        generate_kwargs["language"] = lang

    total = len(file_infos)
    t0 = time.monotonic()

    # Phase 1: parallel audio extraction
    extract_end = progress_start + (progress_end - progress_start) * 0.1
    audio_paths = _extract_all_audio(
        file_infos, progress_cb, progress_start, extract_end
    )

    # Phase 2: GPU inference
    results: list[dict] = []
    infer_start = extract_end
    infer_range = progress_end - infer_start

    for i, info in enumerate(file_infos):
        elapsed = time.monotonic() - t0
        if progress_cb:
            pct = infer_start + infer_range * (i / total)
            progress_cb(
                pct,
                desc=f"Transcribing {i + 1}/{total}  ({elapsed:.0f}s elapsed)",
            )

        try:
            out = pipe(
                audio_paths[i],
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

    elapsed = time.monotonic() - t0
    if progress_cb:
        progress_cb(progress_end, desc=f"Done ({elapsed:.0f}s total)")

    return results
