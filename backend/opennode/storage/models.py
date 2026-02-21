"""Data models for the OpenNode storage layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SessionRecord:
    """Represents a recording session row from the sessions table."""

    id: str
    title: str
    created_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[int]
    language: str
    model_used: str
    audio_source: str  # 'system' | 'microphone' | 'both'
    audio_file_path: Optional[str]
    status: str  # 'active' | 'completed' | 'error'


@dataclass
class TranscriptRecord:
    """Represents a single transcript segment row from the transcripts table."""

    id: int
    session_id: str
    text: str
    speaker: Optional[str]
    start_ms: int
    end_ms: int
    confidence: float
    is_partial: bool
    created_at: datetime


@dataclass
class SummaryRecord:
    """Represents a meeting summary row from the summaries table."""

    id: int
    session_id: str
    executive_summary: str
    key_points: list[str]      # stored as JSON in DB
    action_items: list[str]    # stored as JSON in DB
    decisions: list[str]       # stored as JSON in DB
    next_steps: list[str]      # stored as JSON in DB
    model_used: str
    created_at: datetime


@dataclass
class SpeakerRecord:
    """Represents a speaker row from the speakers table."""

    id: str
    session_id: str
    auto_label: str            # "SPEAKER_00"
    user_label: Optional[str]  # "John"
    color: Optional[str]
    total_duration_ms: int


@dataclass
class SessionWithTranscripts:
    """Aggregated view of a session with all its related data."""

    session: SessionRecord
    transcripts: list[TranscriptRecord]
    summary: Optional[SummaryRecord]
    speakers: list[SpeakerRecord]
