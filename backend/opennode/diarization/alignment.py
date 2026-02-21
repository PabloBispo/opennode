"""Align ASR transcripts with diarization segments."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ..asr.base import TranscriptionResult
from .pyannote_engine import DiarizationSegment, SpeakerProfile, SPEAKER_COLORS

@dataclass
class AnnotatedTranscript:
    text: str
    speaker: Optional[str]
    speaker_label: Optional[str]  # user-assigned or auto
    start_ms: int
    end_ms: int
    confidence: float

def align_transcript_with_speakers(
    transcripts: list[TranscriptionResult],
    diarization: list[DiarizationSegment],
) -> list[AnnotatedTranscript]:
    """
    For each transcript segment, find the speaker with the most temporal overlap.
    """
    annotated = []
    for transcript in transcripts:
        best_speaker = _find_best_speaker(transcript.start_ms, transcript.end_ms, diarization)
        annotated.append(AnnotatedTranscript(
            text=transcript.text,
            speaker=best_speaker,
            speaker_label=best_speaker,
            start_ms=transcript.start_ms,
            end_ms=transcript.end_ms,
            confidence=transcript.confidence,
        ))
    return annotated

def _find_best_speaker(
    start_ms: int,
    end_ms: int,
    segments: list[DiarizationSegment],
) -> Optional[str]:
    """Return the speaker with the most overlap with the given time range."""
    best_speaker: Optional[str] = None
    best_overlap = 0

    for seg in segments:
        overlap_start = max(start_ms, seg.start_ms)
        overlap_end = min(end_ms, seg.end_ms)
        overlap = max(0, overlap_end - overlap_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = seg.speaker

    return best_speaker

def build_speaker_profiles(segments: list[DiarizationSegment]) -> list[SpeakerProfile]:
    """Build speaker profiles from diarization output."""
    profiles: dict[str, SpeakerProfile] = {}
    for i, seg in enumerate(segments):
        if seg.speaker not in profiles:
            color_idx = len(profiles) % len(SPEAKER_COLORS)
            profiles[seg.speaker] = SpeakerProfile(
                id=seg.speaker,
                auto_label=seg.speaker,
                color=SPEAKER_COLORS[color_idx],
                total_duration_ms=0,
            )
        profiles[seg.speaker].total_duration_ms += seg.duration_ms
    return list(profiles.values())
