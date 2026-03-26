"""
Hardware-aware device selection and inference configuration.

Abstracts GPU backend differences so the rest of the pipeline doesn't care
whether it's running on a datacenter A100, a laptop RTX 3060, an M3 MacBook,
or a CPU-only CI runner.

Device priority: CUDA > MPS > CPU

Key design decisions:
- MPS uses float32 because float16 matmuls can produce NaN on certain
  attention patterns in Whisper's cross-attention layers (PyTorch ≤2.3).
- Batch size scales with available VRAM on CUDA. MPS uses unified memory
  shared with the OS, so we stay conservative at 8.
- SDPA (Scaled Dot-Product Attention) is used everywhere — it's the PyTorch-native
  equivalent of Flash Attention 2 and works across all three backends.
"""

from __future__ import annotations

import torch


def detect_device() -> str:
    """Return the best available compute device identifier."""
    if torch.cuda.is_available():
        return "cuda:0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_dtype(device: str) -> torch.dtype:
    """Select optimal dtype for *device*.

    CUDA benefits from float16 (halves memory, enables tensor cores).
    MPS float16 can trigger NaN in Whisper cross-attention — use float32.
    CPU always uses float32.
    """
    if device.startswith("cuda"):
        return torch.float16
    return torch.float32


def get_batch_size(device: str) -> int:
    """Return a safe chunk batch size based on available accelerator memory.

    Whisper's chunked pipeline processes ``batch_size`` 30-second segments in
    parallel.  Larger batches saturate the GPU better but risk OOM on smaller
    cards.  These thresholds follow insanely-fast-whisper defaults (batch_size=24)
    and are tuned for Whisper Large-v3 / distil-large-v3 in float16.
    """
    if device.startswith("cuda"):
        mem = torch.cuda.get_device_properties(0).total_memory
        if mem >= 16 * 1024**3:      # A100 / 4090 / 3090
            return 24
        if mem >= 10 * 1024**3:      # 3060 12 GB / 4070
            return 24
        if mem >= 8 * 1024**3:       # 8 GB cards
            return 16
        return 8                      # smaller cards
    if device == "mps":
        return 16   # unified memory — Apple Silicon can handle more
    return 4        # CPU fallback


def empty_cache(device: str) -> None:
    """Release cached allocator memory after large allocations."""
    if device == "mps":
        torch.mps.empty_cache()
    elif device.startswith("cuda"):
        torch.cuda.empty_cache()


def device_summary(device: str) -> str:
    """Return a human-readable string describing the active device."""
    if device.startswith("cuda"):
        props = torch.cuda.get_device_properties(0)
        vram = props.total_memory / 1024**3
        return f"{props.name} ({vram:.0f} GB)"
    if device == "mps":
        return "Apple Silicon (MPS)"
    return "CPU"


# Module-level singletons — computed once at import time.
DEVICE = detect_device()
DTYPE = get_dtype(DEVICE)
BATCH_SIZE = get_batch_size(DEVICE)
