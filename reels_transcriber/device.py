"""Hardware detection and configuration for CUDA / MPS / CPU."""

import torch


def detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda:0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_dtype(device: str) -> torch.dtype:
    # MPS float16 can produce NaN on some operations; stay safe with float32.
    if device.startswith("cuda"):
        return torch.float16
    return torch.float32


def get_batch_size(device: str) -> int:
    if device.startswith("cuda"):
        mem = torch.cuda.get_device_properties(0).total_memory
        if mem >= 16 * 1024**3:
            return 24
        if mem >= 8 * 1024**3:
            return 16
        return 8
    if device == "mps":
        return 8
    return 4


def empty_cache(device: str) -> None:
    if device == "mps":
        torch.mps.empty_cache()
    elif device.startswith("cuda"):
        torch.cuda.empty_cache()


DEVICE = detect_device()
DTYPE = get_dtype(DEVICE)
BATCH_SIZE = get_batch_size(DEVICE)
