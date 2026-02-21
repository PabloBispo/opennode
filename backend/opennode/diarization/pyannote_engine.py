"""Speaker diarization using pyannote.audio."""
from __future__ import annotations
import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np

try:
    from pyannote.audio import Pipeline
    import torch
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False

@dataclass
class DiarizationSegment:
    speaker: str      # "SPEAKER_00", "SPEAKER_01", ...
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

@dataclass
class SpeakerProfile:
    id: str
    auto_label: str   # "SPEAKER_00"
    user_label: Optional[str] = None
    color: Optional[str] = None
    total_duration_ms: int = 0

# Speaker color palette
SPEAKER_COLORS = [
    "#3B82F6",  # blue
    "#10B981",  # green
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # purple
    "#06B6D4",  # cyan
    "#F97316",  # orange
    "#EC4899",  # pink
    "#84CC16",  # lime
    "#14B8A6",  # teal
]

class DiarizationEngine:
    """
    Wraps pyannote.audio speaker-diarization-3.1 pipeline.

    Requires:
      - pyannote.audio >= 3.1
      - HuggingFace token with accepted license at:
        https://huggingface.co/pyannote/speaker-diarization-3.1
    """

    def __init__(self, hf_token: str = "", max_speakers: int = 10):
        if not PYANNOTE_AVAILABLE:
            raise ImportError(
                "pyannote.audio is required for speaker diarization. "
                "Install with: pip install pyannote.audio"
            )
        self.max_speakers = max_speakers
        self.hf_token = hf_token
        self._pipeline: Optional["Pipeline"] = None  # type: ignore[type-arg]
        self._is_loaded = False

    def load_model(self) -> None:
        """Load pyannote pipeline. Requires HF token."""
        self._pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=self.hf_token or None,
        )
        if torch.cuda.is_available():
            self._pipeline.to(torch.device("cuda"))
        self._is_loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    async def diarize(self, audio_path: str | Path) -> list[DiarizationSegment]:
        """Run diarization on a complete audio file."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._diarize_sync, str(audio_path))

    def _diarize_sync(self, audio_path: str) -> list[DiarizationSegment]:
        assert self._pipeline is not None
        result = self._pipeline(audio_path, max_speakers=self.max_speakers)
        segments = []
        for turn, _, speaker in result.itertracks(yield_label=True):
            segments.append(DiarizationSegment(
                speaker=speaker,
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000),
            ))
        return segments

    async def diarize_buffer(self, audio: np.ndarray, sample_rate: int = 16000) -> list[DiarizationSegment]:
        """Run diarization on a numpy audio buffer (writes temp file)."""
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError("soundfile is required: pip install soundfile")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            sf.write(tmp_path, audio, sample_rate)
            return await self.diarize(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def unload_model(self) -> None:
        self._pipeline = None
        self._is_loaded = False
