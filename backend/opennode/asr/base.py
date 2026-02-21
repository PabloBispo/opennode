"""Abstract base class and data models for ASR engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class WordTimestamp:
    """Represents a single word with timing and confidence information."""

    word: str
    start_ms: int
    end_ms: int
    confidence: float


@dataclass
class TranscriptionResult:
    """The result of a transcription operation."""

    text: str
    confidence: float
    language: str
    start_ms: int
    end_ms: int
    words: list[WordTimestamp] = field(default_factory=list)
    is_partial: bool = False


class ASREngine(ABC):
    """Abstract base class defining the interface for all ASR engines.

    Subclasses must implement all abstract methods. The load/unload lifecycle
    allows engines to manage expensive resources (models, GPU memory) explicitly.
    """

    @abstractmethod
    async def load_model(self) -> None:
        """Load the ASR model into memory (and GPU if available).

        Raises:
            ImportError: If the required backend library is not installed.
            RuntimeError: If the model cannot be loaded for any other reason.
        """
        ...

    @abstractmethod
    async def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe a complete audio segment.

        Args:
            audio: 1-D float32 numpy array of audio samples.
            sample_rate: Sample rate in Hz. Must match the engine's expected rate.

        Returns:
            A TranscriptionResult with text, timing, and word-level details.
        """
        ...

    @abstractmethod
    async def transcribe_stream(
        self, audio_chunk: np.ndarray
    ) -> TranscriptionResult:
        """Transcribe an incremental audio chunk (for streaming mode).

        Args:
            audio_chunk: 1-D float32 numpy array of a single audio chunk.

        Returns:
            A TranscriptionResult (may be partial if streaming is in progress).
        """
        ...

    @abstractmethod
    def unload_model(self) -> None:
        """Release model resources (GPU memory, file handles, etc.)."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if the model is currently loaded and ready for inference."""
        ...

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return True if this engine supports incremental/streaming transcription."""
        ...
