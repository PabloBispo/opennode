"""ASR engine package.

Public API
----------
- :class:`ASREngine` — abstract base class
- :class:`TranscriptionResult` — result dataclass
- :class:`WordTimestamp` — per-word timing dataclass
- :func:`create_asr_engine` — factory function
"""

from .base import ASREngine, TranscriptionResult, WordTimestamp
from .factory import create_asr_engine

__all__ = [
    "ASREngine",
    "TranscriptionResult",
    "WordTimestamp",
    "create_asr_engine",
]
