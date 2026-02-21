"""Speaker diarization package."""
from .pyannote_engine import (
    DiarizationEngine,
    DiarizationSegment,
    SpeakerProfile,
    PYANNOTE_AVAILABLE,
    SPEAKER_COLORS,
)
from .alignment import (
    AnnotatedTranscript,
    align_transcript_with_speakers,
    build_speaker_profiles,
)

__all__ = [
    "DiarizationEngine",
    "DiarizationSegment",
    "SpeakerProfile",
    "PYANNOTE_AVAILABLE",
    "SPEAKER_COLORS",
    "AnnotatedTranscript",
    "align_transcript_with_speakers",
    "build_speaker_profiles",
]
