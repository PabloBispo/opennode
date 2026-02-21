import pytest
import numpy as np

def test_diarization_segment_duration():
    from opennode.diarization import DiarizationSegment
    seg = DiarizationSegment(speaker="SPEAKER_00", start_ms=0, end_ms=5000)
    assert seg.duration_ms == 5000

def test_speaker_profile_defaults():
    from opennode.diarization import SpeakerProfile
    p = SpeakerProfile(id="SPEAKER_00", auto_label="SPEAKER_00")
    assert p.user_label is None
    assert p.total_duration_ms == 0

def test_pyannote_not_available_raises():
    from opennode.diarization import PYANNOTE_AVAILABLE, DiarizationEngine
    if not PYANNOTE_AVAILABLE:
        with pytest.raises(ImportError, match="pyannote.audio"):
            DiarizationEngine()

def test_pyannote_available_flag_is_bool():
    from opennode.diarization import PYANNOTE_AVAILABLE
    assert isinstance(PYANNOTE_AVAILABLE, bool)

def test_align_transcript_with_speakers_basic():
    from opennode.diarization import align_transcript_with_speakers, DiarizationSegment
    from opennode.asr.base import TranscriptionResult
    transcripts = [
        TranscriptionResult(text="Hello", confidence=0.9, language="en", start_ms=0, end_ms=1000),
        TranscriptionResult(text="World", confidence=0.9, language="en", start_ms=2000, end_ms=3000),
    ]
    diarization = [
        DiarizationSegment(speaker="SPEAKER_00", start_ms=0, end_ms=1500),
        DiarizationSegment(speaker="SPEAKER_01", start_ms=1500, end_ms=3500),
    ]
    annotated = align_transcript_with_speakers(transcripts, diarization)
    assert len(annotated) == 2
    assert annotated[0].speaker == "SPEAKER_00"
    assert annotated[1].speaker == "SPEAKER_01"

def test_align_empty_diarization():
    from opennode.diarization import align_transcript_with_speakers
    from opennode.asr.base import TranscriptionResult
    transcripts = [
        TranscriptionResult(text="Hello", confidence=0.9, language="en", start_ms=0, end_ms=1000),
    ]
    annotated = align_transcript_with_speakers(transcripts, [])
    assert annotated[0].speaker is None

def test_build_speaker_profiles():
    from opennode.diarization import build_speaker_profiles, DiarizationSegment, SPEAKER_COLORS
    segments = [
        DiarizationSegment(speaker="SPEAKER_00", start_ms=0, end_ms=1000),
        DiarizationSegment(speaker="SPEAKER_01", start_ms=1000, end_ms=2000),
        DiarizationSegment(speaker="SPEAKER_00", start_ms=2000, end_ms=3000),
    ]
    profiles = build_speaker_profiles(segments)
    assert len(profiles) == 2
    spk00 = next(p for p in profiles if p.id == "SPEAKER_00")
    assert spk00.total_duration_ms == 2000
    assert spk00.color is not None
    assert spk00.color in SPEAKER_COLORS

def test_annotated_transcript_fields():
    from opennode.diarization.alignment import AnnotatedTranscript
    t = AnnotatedTranscript(
        text="Hello", speaker="SPEAKER_00", speaker_label="John",
        start_ms=0, end_ms=500, confidence=0.95
    )
    assert t.text == "Hello"
    assert t.speaker_label == "John"
