"""Silero VAD wrapper for real-time speech detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import torch
    from silero_vad import load_silero_vad, get_speech_timestamps

    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False


@dataclass
class VADResult:
    """Result of processing a single audio chunk through VAD."""

    is_speech: bool
    probability: float
    audio: np.ndarray


@dataclass
class SpeechSegment:
    """A detected speech segment with start/end sample indices at 16kHz."""

    start: int  # sample index at 16kHz
    end: int  # sample index at 16kHz

    @property
    def duration_ms(self) -> float:
        """Duration of the segment in milliseconds."""
        return (self.end - self.start) / 16.0  # 16kHz -> ms


class SileroVAD:
    """Silero VAD wrapper for real-time speech detection.

    Uses the Silero VAD model to detect speech in audio chunks.
    Processes 512-sample (32ms at 16kHz) chunks for optimal performance.

    Requires silero-vad and torch to be installed:
        pip install silero-vad torch
    """

    CHUNK_SIZE = 512  # 32ms at 16kHz (Silero's optimal chunk size)

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000) -> None:
        """Initialize Silero VAD.

        Args:
            threshold: Speech probability threshold (0.0–1.0). Default 0.5.
            sample_rate: Audio sample rate in Hz. Must be 16000 for Silero.

        Raises:
            ImportError: If silero-vad or torch are not installed.
        """
        if not SILERO_AVAILABLE:
            raise ImportError(
                "silero-vad and torch are required. "
                "Install with: pip install silero-vad torch"
            )
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.model = load_silero_vad()
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the internal model state."""
        self.model.reset_states()

    def process_chunk(self, audio_chunk: np.ndarray) -> VADResult:
        """Process a 512-sample (32ms) audio chunk.

        Args:
            audio_chunk: Float32 numpy array of CHUNK_SIZE samples.

        Returns:
            VADResult with speech detection result.
        """
        tensor = torch.from_numpy(audio_chunk.astype(np.float32))
        prob = self.model(tensor, self.sample_rate).item()
        return VADResult(
            is_speech=prob >= self.threshold,
            probability=prob,
            audio=audio_chunk,
        )

    def get_speech_segments(self, audio: np.ndarray) -> list[SpeechSegment]:
        """Get speech timestamps from a full audio array.

        Args:
            audio: Float32 numpy array with the full audio signal.

        Returns:
            List of SpeechSegment objects with start/end sample indices.
        """
        tensor = torch.from_numpy(audio.astype(np.float32))
        timestamps = get_speech_timestamps(
            tensor,
            self.model,
            threshold=self.threshold,
            sampling_rate=self.sample_rate,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100,
            speech_pad_ms=30,
        )
        self._reset_state()
        return [SpeechSegment(start=t["start"], end=t["end"]) for t in timestamps]

    def reset(self) -> None:
        """Reset internal model state. Call between independent audio streams."""
        self._reset_state()
