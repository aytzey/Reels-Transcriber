"""
Insanely-fast Whisper inference engine with hardware-aware batching.

Technique adapted from https://github.com/Vaibhavs10/insanely-fast-whisper:
- HuggingFace Transformers ASR pipeline with Flash Attention 2 / SDPA
- float16 precision on CUDA for tensor core acceleration
- Auto-scaled batching of 30-second chunks from available VRAM
- Stride overlap between chunks for seamless boundaries
- Batched multi-file processing (all files in a single pipeline pass)
- Automatic OOM recovery with batch size halving

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

_log_t = _log.getLogger("reels_transcriber.transcriber")


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
    """Convert any media file to 16 kHz mono WAV via ffmpeg.

    Returns the WAV path on success, or the original path as a fallback
    so the pipeline can still attempt to read it.
    """
    wav = video_path.rsplit(".", 1)[0] + ".wav"
    if os.path.exists(wav):
        return wav
    try:
        result = subprocess.run(
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
        if result.returncode != 0:
            _log_t.warning("ffmpeg failed for %s: %s", video_path, result.stderr[:200])
    except subprocess.TimeoutExpired:
        _log_t.warning("ffmpeg timed out for %s", video_path)
    except FileNotFoundError:
        _log_t.error("ffmpeg not found — install ffmpeg to enable audio extraction")
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
            except Exception as exc:
                _log_t.warning("Audio extraction failed for %s: %s", paths[idx], exc)
                audio_paths[idx] = paths[idx]
            done += 1
            if progress_cb:
                pct = progress_start + (progress_extract_end - progress_start) * (done / total)
                progress_cb(pct, desc=f"Extracting audio ({done}/{total})...")

    return [p or paths[i] for i, p in enumerate(audio_paths)]


# ---------------------------------------------------------------------------
# OOM-safe inference with automatic batch size halving
# ---------------------------------------------------------------------------

def _run_inference(pipe, audio_paths: list[str], batch_size: int, generate_kwargs: dict):
    """Run the ASR pipeline with automatic OOM recovery.

    If CUDA runs out of memory, halves the batch_size and retries (up to
    3 times).  This makes the pipeline resilient across GPUs without manual
    tuning — a 4 GB card will just use a smaller batch automatically.
    """
    current_bs = batch_size
    last_error = None

    for attempt in range(4):
        try:
            empty_cache(DEVICE)
            with torch.inference_mode():
                outputs = pipe(
                    audio_paths,
                    chunk_length_s=30,
                    stride_length_s=(6, 2),
                    batch_size=current_bs,
                    generate_kwargs=generate_kwargs,
                    return_timestamps=True,
                )
            return outputs
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and current_bs > 1:
                last_error = exc
                old_bs = current_bs
                current_bs = max(1, current_bs // 2)
                _log_t.warning(
                    "OOM at batch_size=%d, retrying with %d (attempt %d/3)",
                    old_bs, current_bs, attempt + 1,
                )
                empty_cache(DEVICE)
                continue
            raise
        except Exception:
            raise

    raise RuntimeError(
        f"Inference failed after 4 OOM retries (last batch_size=1): {last_error}"
    )


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
    2. Run batched Whisper inference on GPU with OOM auto-recovery.

    Key optimizations (from insanely-fast-whisper):
    - torch.inference_mode() for faster inference (no grad tracking)
    - chunk_length_s=30 with stride_length_s=(6, 2) for overlapping chunks
    - Auto-scaled batch_size for maximum GPU utilization
    - All files processed in a single pipeline pass (batched dataset mode)
    - Automatic batch_size halving on CUDA OOM
    """
    if not file_infos:
        return []

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

    # Phase 2: GPU inference — insanely-fast-whisper batched approach with OOM safety
    infer_start = extract_end
    infer_range = progress_end - infer_start

    if progress_cb:
        progress_cb(
            infer_start,
            desc=f"Transcribing {total} file{'s' if total > 1 else ''} (batch_size={BATCH_SIZE})...",
        )

    raw_outputs = _run_inference(pipe, audio_paths, BATCH_SIZE, generate_kwargs)

    # pipe() returns a single dict for 1 input, list of dicts for multiple
    if isinstance(raw_outputs, dict):
        raw_outputs = [raw_outputs]

    # Build result list with per-file error isolation
    results: list[dict] = []
    for i, info in enumerate(file_infos):
        if progress_cb:
            pct = infer_start + infer_range * ((i + 1) / total)
            elapsed = time.monotonic() - t0
            progress_cb(pct, desc=f"Processing results ({i + 1}/{total}, {elapsed:.0f}s)")

        try:
            out = raw_outputs[i]
            text = out.get("text", "").strip() if isinstance(out, dict) else ""
            chunks = out.get("chunks", []) if isinstance(out, dict) else []
        except (IndexError, AttributeError) as exc:
            _log_t.warning("Result parsing failed for file %d: %s", i, exc)
            text = ""
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
                if isinstance(c, dict)
            ],
        })

    elapsed = time.monotonic() - t0
    if progress_cb:
        avg = elapsed / total if total else 0
        progress_cb(
            progress_end,
            desc=f"Done — {total} file{'s' if total > 1 else ''} in {elapsed:.0f}s ({avg:.1f}s/file)",
        )

    return results
