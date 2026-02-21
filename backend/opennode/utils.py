"""Utility functions for OpenNode backend."""

from __future__ import annotations

from typing import Any


def check_gpu() -> dict[str, Any]:
    """Check if CUDA GPU is available and return device info."""
    try:
        import torch

        if torch.cuda.is_available():
            device = torch.cuda.get_device_properties(0)
            return {
                "available": True,
                "name": device.name,
                "vram_mb": device.total_memory // (1024 * 1024),
                "compute_capability": f"{device.major}.{device.minor}",
            }
    except ImportError:
        pass

    return {"available": False, "name": None, "vram_mb": None, "compute_capability": None}
