"""
Insanely-fast Whisper inference engine with hardware-aware batching.

Technique adapted from https://github.com/Vaibhavs10/insanely-fast-whisper:
- HuggingFace Transformers ASR pipeline with Flash Attention 2 / SDPA
- float16 precision on CUDA for tensor core acceleration
- Aggressive batching of 30-second chunks (batch_size=24)
- Stride overlap between chunks for seamless boundaries
- Batched multi-file processing (all files in a single pipeline pass)

Pipeline: video -> parallel ffmpeg extraction -> batched ASR -> text
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

import torch
from transformers import pipeline as hf_pipeline

from .device import DEVICE, DTYPE, BATCH_SIZE, empty_cache

# Model options — distil-large-v3 is ~6x faster than large-v3 with similar quality.
# Follows insanely-fast-whisper's recommendation.
MODEL_DISTIL = "distil-whisper/distil-large-v3"
MODEL_LARGE = "openai/whisper-large-v3"
MODEL_NAME = MODEL_DISTIL  # default to fast model

_pipe = None
_current_model = None
_lock = threading.Lock()


def _detect_attn_impl() -> str:
    """Pick the best available attention implementation.

    Matches insanely-fast-whisper: flash_attention_2 on supported CUDA GPUs,
    SDPA fallback everywhere else (equivalent to BetterTransformer).
    """
    if not DEVICE.startswith("cuda"):
        return "sdpa"
    try:
        import flash_attn  # noqa: F401
        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def load_model(model_name: str | None = None):
    """Eagerly load the Whisper pipeline. Safe to call multiple times.

    Uses insanely-fast-whisper technique:
    - low_cpu_mem_usage for faster loading
    - Flash Attention 2 / SDPA for optimized attention
    - float16 on CUDA for tensor core acceleration
    """
    global _pipe, _current_model
    target = model_name or MODEL_NAME

    if _pipe is not None and _current_model == target:
        return _pipe

    with _lock:
        if _pipe is not None and _current_model == target:
            return _pipe

        # Release old model memory before loading new one
        if _pipe is not None:
            del _pipe
            _pipe = None
            _current_model = None
            empty_cache(DEVICE)

        attn = _detect_attn_impl()
        _pipe = hf_pipeline(
            "automatic-speech-recognition",
            model=target,
            torch_dtype=DTYPE,
            device=DEVICE,
            model_kwargs={
                "attn_implementation": attn,
                "low_cpu_mem_usage": True,
            },
        )
        _current_model = target
        empty_cache(DEVICE)
        print(f"  Model    : {target}")
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
# Transcription — insanely-fast-whisper technique
# ---------------------------------------------------------------------------

def transcribe(
    file_infos: list[dict],
    language: str = "auto",
    progress_cb: Callable | None = None,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
    model_name: str | None = None,
) -> list[dict]:
    """Transcribe a batch of video/audio files using insanely-fast-whisper technique.

    1. Extract audio from all files in parallel (threaded ffmpeg).
    2. Run batched Whisper inference on GPU with all files passed to the
       pipeline simultaneously for maximum throughput.

    Key optimizations (from insanely-fast-whisper):
    - torch.inference_mode() for faster inference (no grad tracking)
    - chunk_length_s=30 with stride_length_s=(6, 2) for overlapping chunks
    - Aggressive batch_size for maximum GPU utilization
    - All files processed in a single pipeline pass (batched dataset mode)
    """
    pipe = load_model(model_name)
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

    # Phase 2: GPU inference — insanely-fast-whisper batched approach
    infer_start = extract_end
    infer_range = progress_end - infer_start

    if progress_cb:
        progress_cb(infer_start, desc=f"Transcribing {total} files (batched)...")

    # Process all files in a single batched pipeline pass.
    # torch.inference_mode() disables autograd entirely — faster than no_grad.
    with torch.inference_mode():
        raw_outputs = pipe(
            audio_paths,
            chunk_length_s=30,
            stride_length_s=(6, 2),
            batch_size=BATCH_SIZE,
            generate_kwargs=generate_kwargs,
            return_timestamps=True,
        )

    # Build result list
    results: list[dict] = []

    # pipe() returns a single dict for 1 input, list of dicts for multiple
    if isinstance(raw_outputs, dict):
        raw_outputs = [raw_outputs]

    for i, (info, out) in enumerate(zip(file_infos, raw_outputs)):
        if progress_cb:
            pct = infer_start + infer_range * ((i + 1) / total)
            elapsed = time.monotonic() - t0
            progress_cb(pct, desc=f"Processing results ({i + 1}/{total}, {elapsed:.0f}s)")

        try:
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
