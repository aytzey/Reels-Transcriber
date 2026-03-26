"""
Hardware-aware device selection and inference configuration.

Abstracts GPU backend differences so the rest of the pipeline doesn't care
whether it's running on a datacenter A100, a laptop RTX 3060, an M3 MacBook,
or a CPU-only CI runner.

Device priority: CUDA > MPS > CPU

Batch size is computed dynamically from available VRAM — not hardcoded per GPU.
The formula reserves memory for model weights + OS overhead and allocates the
rest to inference batches.  This means it auto-scales correctly on any GPU
from a 4 GB GTX 1650 to an 80 GB A100.

Key design decisions:
- MPS uses float32 because float16 matmuls can produce NaN on certain
  attention patterns in Whisper's cross-attention layers (PyTorch ≤2.3).
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
    """Auto-compute optimal batch size from available GPU memory.

    Each 30-second Whisper chunk uses roughly 275 MB VRAM in float16.
    We reserve ~3.5 GB for model weights (distil-large-v3 / large-v3 in fp16)
    plus ~0.5 GB OS/driver overhead, then fill the rest with batches.

    Clamps to [1, 32] — going above 32 gives diminishing returns and can
    trigger CUDA OOM on edge cases.
    """
    if device.startswith("cuda"):
        idx = int(device.split(":")[-1]) if ":" in device else 0
        total_mem = torch.cuda.get_device_properties(idx).total_memory
        free_mem = total_mem - 4 * 1024**3  # reserve ~4 GB for model + overhead
        if free_mem <= 0:
            return 1
        chunk_cost = 275 * 1024**2  # ~275 MB per batch slot in fp16
        batch = int(free_mem // chunk_cost)
        return max(1, min(batch, 32))

    if device == "mps":
        # Apple unified memory — query total system RAM, use 25% for batching
        try:
            import psutil
            total_ram = psutil.virtual_memory().total
        except ImportError:
            # psutil not available — safe default
            total_ram = 8 * 1024**3
        usable = total_ram * 0.25 - 4 * 1024**3  # reserve model + OS
        if usable <= 0:
            return 4
        chunk_cost = 550 * 1024**2  # fp32 chunks use ~2x memory
        batch = int(usable // chunk_cost)
        return max(4, min(batch, 16))

    return 2  # CPU fallback — RAM is plentiful but inference is slow


def empty_cache(device: str) -> None:
    """Release cached allocator memory after large allocations."""
    if device == "mps":
        torch.mps.empty_cache()
    elif device.startswith("cuda"):
        torch.cuda.empty_cache()


def device_summary(device: str) -> str:
    """Return a human-readable string describing the active device."""
    if device.startswith("cuda"):
        idx = int(device.split(":")[-1]) if ":" in device else 0
        props = torch.cuda.get_device_properties(idx)
        vram = props.total_memory / 1024**3
        return f"{props.name} ({vram:.0f} GB)"
    if device == "mps":
        return "Apple Silicon (MPS)"
    return "CPU"


# Module-level singletons — computed once at import time.
DEVICE = detect_device()
DTYPE = get_dtype(DEVICE)
BATCH_SIZE = get_batch_size(DEVICE)
