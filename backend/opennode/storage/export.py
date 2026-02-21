"""Export functions for meeting sessions in various formats."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from .models import SessionWithTranscripts, TranscriptRecord


# ─── Time formatting helpers ──────────────────────────────────────────────────


def format_duration(ms: int) -> str:
    """Format milliseconds as HH:MM:SS (omitting hours if zero) or MM:SS.

    Examples
    --------
    >>> format_duration(90000)
    '01:30'
    >>> format_duration(3661000)
    '01:01:01'
    """
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_timestamp(ms: int) -> str:
    """Format milliseconds as [HH:MM:SS] for inline transcript labels.

    Examples
    --------
    >>> format_timestamp(65000)
    '[00:01:05]'
    """
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"


def format_srt_time(ms: int) -> str:
    """Format milliseconds as HH:MM:SS,mmm for SRT subtitle files.

    Examples
    --------
    >>> format_srt_time(1500)
    '00:00:01,500'
    >>> format_srt_time(61234)
    '00:01:01,234'
    """
    hours = ms // 3_600_000
    remaining = ms % 3_600_000
    minutes = remaining // 60_000
    remaining = remaining % 60_000
    seconds = remaining // 1_000
    millis = remaining % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


# ─── Export functions ─────────────────────────────────────────────────────────


def export_markdown(session: SessionWithTranscripts) -> str:
    """Export a session as a Markdown document.

    The document includes:
    - Title and metadata header
    - Summary section (if available)
    - Full transcript with speaker labels and timestamps
    """
    s = session.session
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(f"# {s.title}")
    lines.append("")
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Date:** {s.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- **Language:** {s.language}")
    lines.append(f"- **Model:** {s.model_used}")
    lines.append(f"- **Audio source:** {s.audio_source}")
    if s.duration_ms is not None:
        lines.append(f"- **Duration:** {format_duration(s.duration_ms)}")
    lines.append(f"- **Status:** {s.status}")
    lines.append("")

    # ── Summary ───────────────────────────────────────────────────────────
    if session.summary is not None:
        sm = session.summary
        lines.append("## Summary")
        lines.append("")
        lines.append(sm.executive_summary)
        lines.append("")

        if sm.key_points:
            lines.append("### Key Points")
            lines.append("")
            for point in sm.key_points:
                lines.append(f"- {point}")
            lines.append("")

        if sm.action_items:
            lines.append("### Action Items")
            lines.append("")
            for item in sm.action_items:
                lines.append(f"- [ ] {item}")
            lines.append("")

        if sm.decisions:
            lines.append("### Decisions")
            lines.append("")
            for decision in sm.decisions:
                lines.append(f"- {decision}")
            lines.append("")

        if sm.next_steps:
            lines.append("### Next Steps")
            lines.append("")
            for step in sm.next_steps:
                lines.append(f"- {step}")
            lines.append("")

    # ── Transcript ────────────────────────────────────────────────────────
    lines.append("## Transcript")
    lines.append("")

    if not session.transcripts:
        lines.append("*(No transcript available)*")
    else:
        for segment in session.transcripts:
            timestamp = format_timestamp(segment.start_ms)
            speaker = segment.speaker or "Unknown"
            lines.append(f"**{speaker}** {timestamp}")
            lines.append(f"> {segment.text}")
            lines.append("")

    return "\n".join(lines)


def export_srt(session: SessionWithTranscripts) -> str:
    """Export a session as an SRT subtitle file.

    Each non-partial transcript segment becomes a numbered subtitle block.
    """
    blocks: list[str] = []

    for index, segment in enumerate(session.transcripts, start=1):
        start = format_srt_time(segment.start_ms)
        # Ensure end is at least 1 ms after start to keep valid SRT
        end_ms = max(segment.end_ms, segment.start_ms + 1)
        end = format_srt_time(end_ms)

        text = segment.text
        if segment.speaker:
            text = f"[{segment.speaker}] {text}"

        blocks.append(f"{index}")
        blocks.append(f"{start} --> {end}")
        blocks.append(text)
        blocks.append("")

    return "\n".join(blocks)


def export_json(session: SessionWithTranscripts) -> dict:  # type: ignore[type-arg]
    """Export a session as a structured JSON-serialisable dictionary."""
    s = session.session

    def _dt(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt is not None else None

    transcripts_data = [
        {
            "id": t.id,
            "text": t.text,
            "speaker": t.speaker,
            "start_ms": t.start_ms,
            "end_ms": t.end_ms,
            "confidence": t.confidence,
            "is_partial": t.is_partial,
            "created_at": _dt(t.created_at),
        }
        for t in session.transcripts
    ]

    summary_data = None
    if session.summary is not None:
        sm = session.summary
        summary_data = {
            "executive_summary": sm.executive_summary,
            "key_points": sm.key_points,
            "action_items": sm.action_items,
            "decisions": sm.decisions,
            "next_steps": sm.next_steps,
            "model_used": sm.model_used,
            "created_at": _dt(sm.created_at),
        }

    speakers_data = [
        {
            "id": sp.id,
            "auto_label": sp.auto_label,
            "user_label": sp.user_label,
            "color": sp.color,
            "total_duration_ms": sp.total_duration_ms,
        }
        for sp in session.speakers
    ]

    return {
        "session": {
            "id": s.id,
            "title": s.title,
            "created_at": _dt(s.created_at),
            "ended_at": _dt(s.ended_at),
            "duration_ms": s.duration_ms,
            "language": s.language,
            "model_used": s.model_used,
            "audio_source": s.audio_source,
            "audio_file_path": s.audio_file_path,
            "status": s.status,
        },
        "transcripts": transcripts_data,
        "summary": summary_data,
        "speakers": speakers_data,
    }


def export_txt(session: SessionWithTranscripts) -> str:
    """Export a session as plain text with minimal formatting.

    Each transcript line is prefixed with a timestamp and optional speaker label.
    """
    s = session.session
    lines: list[str] = []

    lines.append(s.title.upper())
    lines.append("=" * max(len(s.title), 40))
    lines.append(f"Date: {s.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    if s.duration_ms is not None:
        lines.append(f"Duration: {format_duration(s.duration_ms)}")
    lines.append("")

    if session.summary is not None:
        sm = session.summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(sm.executive_summary)
        lines.append("")

        if sm.action_items:
            lines.append("ACTION ITEMS")
            for item in sm.action_items:
                lines.append(f"  - {item}")
            lines.append("")

    lines.append("TRANSCRIPT")
    lines.append("-" * 40)

    if not session.transcripts:
        lines.append("(No transcript available)")
    else:
        for segment in session.transcripts:
            timestamp = format_timestamp(segment.start_ms)
            if segment.speaker:
                lines.append(f"{timestamp} {segment.speaker}: {segment.text}")
            else:
                lines.append(f"{timestamp} {segment.text}")

    lines.append("")
    return "\n".join(lines)
