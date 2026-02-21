"""ASR engine factory — selects and instantiates the right engine."""

from __future__ import annotations

from loguru import logger

from ..config import Settings
from .base import ASREngine


def _gpu_available() -> bool:
    """Return True if a CUDA GPU is available."""
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def create_asr_engine(config: Settings) -> ASREngine:
    """Select and instantiate the appropriate ASR engine based on *config*.

    Selection logic
    ---------------
    - ``config.asr_engine == "parakeet"``:
        Try to use :class:`ParakeetEngine` (requires GPU + NeMo).
        If NeMo is not installed or no GPU is available, fall back to
        :class:`OnnxParakeetEngine` (CPU INT8).
    - ``config.asr_engine == "whisper"``:
        Use :class:`WhisperEngine`.  Raises :class:`ImportError` if
        faster-whisper is not installed.
    - ``config.asr_engine == "onnx"``:
        Use :class:`OnnxParakeetEngine` directly.
    - Any other value raises :class:`ValueError`.

    Args:
        config: Application settings (reads ``asr_engine`` field).

    Returns:
        An uninitialised ASREngine instance (call ``await engine.load_model()``
        before use).

    Raises:
        ValueError: If ``config.asr_engine`` is not a recognised engine name.
        ImportError: If the required backend library is not installed.
    """
    engine_name = config.asr_engine.lower()

    if engine_name == "parakeet":
        return _create_parakeet_or_onnx()

    if engine_name == "whisper":
        return _create_whisper()

    if engine_name == "onnx":
        return _create_onnx()

    raise ValueError(
        f"Unknown ASR engine: '{config.asr_engine}'. "
        "Valid options are: 'parakeet', 'whisper', 'onnx'."
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_parakeet_or_onnx() -> ASREngine:
    """Return ParakeetEngine (GPU) or OnnxParakeetEngine (CPU) as appropriate."""
    from .parakeet import NEMO_AVAILABLE, ParakeetEngine

    if NEMO_AVAILABLE and _gpu_available():
        logger.info("NeMo available and GPU detected — using Parakeet (GPU).")
        return ParakeetEngine()

    # Fall back to ONNX CPU engine.
    logger.info(
        "NeMo unavailable or no GPU detected — falling back to ONNX Parakeet (CPU)."
    )
    return _create_onnx()


def _create_whisper() -> ASREngine:
    """Return a WhisperEngine, raising ImportError if not installed."""
    from .whisper import FASTER_WHISPER_AVAILABLE, WhisperEngine

    if not FASTER_WHISPER_AVAILABLE:
        raise ImportError(
            "faster-whisper is not installed. "
            "Install it with: pip install 'opennode-backend[whisper]'"
        )

    logger.info("Using Whisper engine (faster-whisper).")
    return WhisperEngine()


def _create_onnx() -> ASREngine:
    """Return an OnnxParakeetEngine, raising ImportError if not installed."""
    from .onnx_parakeet import ONNX_ASR_AVAILABLE, OnnxParakeetEngine

    if not ONNX_ASR_AVAILABLE:
        raise ImportError(
            "onnx-asr is not installed. "
            "Install it with: pip install 'opennode-backend[cpu]'"
        )

    logger.info("Using ONNX Parakeet engine (CPU, INT8).")
    return OnnxParakeetEngine()
