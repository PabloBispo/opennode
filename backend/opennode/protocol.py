"""Pydantic models for the OpenNode WebSocket protocol.

These mirror the TypeScript types in electron/src/shared/types.ts.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


# ─── Client → Server ─────────────────────────────────────────────────────────


class CaptureConfig(BaseModel):
    language: str = "auto"
    model: Literal["parakeet", "whisper"] = "parakeet"
    enable_diarization: bool = True


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    data: str  # base64 PCM 16-bit 16kHz mono
    timestamp: int  # Unix ms
    session_id: str


class ControlMessage(BaseModel):
    type: Literal["control"] = "control"
    action: Literal["start", "stop", "pause", "resume"]
    session_id: str
    config: Optional[CaptureConfig] = None


# ─── Server → Client ─────────────────────────────────────────────────────────


class WordTimestamp(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    confidence: float


class PartialTranscriptMessage(BaseModel):
    type: Literal["partial_transcript"] = "partial_transcript"
    text: str
    chunk_id: int
    confidence: float
    timestamp_ms: int


class FinalTranscriptMessage(BaseModel):
    type: Literal["final_transcript"] = "final_transcript"
    text: str
    chunk_id: int
    confidence: float
    speaker: Optional[str] = None
    start_ms: int
    end_ms: int
    words: Optional[list[WordTimestamp]] = None


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    state: Literal["ready", "transcribing", "paused", "error"]
    model_loaded: bool
    gpu_available: bool
    error: Optional[str] = None


class SummaryMessage(BaseModel):
    type: Literal["summary"] = "summary"
    session_id: str
    summary: str
    action_items: list[str]
    key_decisions: list[str]
