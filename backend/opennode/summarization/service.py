"""SummarizationService: orchestrates summarization for sessions."""
from __future__ import annotations
from typing import Optional
from loguru import logger
from ..config import Settings
from ..storage.database import Database
from ..storage.models import TranscriptRecord
from .summarizer import MeetingSummary, OllamaSummarizer, APISummarizer, Summarizer


def format_transcript_for_summary(transcripts: list[TranscriptRecord], max_chars: int = 400_000) -> str:
    """Format transcript records into a readable string."""
    lines = []
    for t in transcripts:
        ms = t.start_ms
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s = ms // 1000
        ts = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        speaker = t.speaker or "Unknown"
        lines.append(f"[{ts}] {speaker}: {t.text}")

    full = "\n".join(lines)
    if len(full) > max_chars:
        # Keep the last max_chars characters (most recent content)
        full = "...[transcript truncated]...\n" + full[-max_chars:]
    return full


def build_speaker_list(transcripts: list[TranscriptRecord]) -> list[str]:
    """Extract unique speaker names from transcripts."""
    seen: list[str] = []
    for t in transcripts:
        if t.speaker and t.speaker not in seen:
            seen.append(t.speaker)
    return seen


class SummarizationService:
    """Orchestrates summarization: loads transcript, summarizes, saves result."""

    def __init__(self, config: Settings):
        self._config = config
        self._summarizer: Optional[Summarizer] = None

    def _get_summarizer(self) -> Summarizer:
        if self._summarizer:
            return self._summarizer
        cfg = self._config
        if cfg.summarization_provider == "ollama":
            self._summarizer = OllamaSummarizer(
                model=cfg.ollama_model,
                base_url=cfg.ollama_url,
            )
        else:
            # Requires api_key — not in Settings by default; passed via env or future config
            import os
            api_key = os.getenv(f"{cfg.summarization_provider.upper()}_API_KEY", "")
            self._summarizer = APISummarizer(
                provider=cfg.summarization_provider,
                api_key=api_key,
                model="",
            )
        return self._summarizer

    async def summarize_session(self, session_id: str, db: Database) -> Optional[MeetingSummary]:
        """Load session transcripts and run summarization."""
        transcripts = await db.get_transcripts(session_id, include_partials=False)
        if not transcripts:
            logger.warning(f"No transcripts found for session {session_id}")
            return None

        speakers = build_speaker_list(transcripts)
        formatted = format_transcript_for_summary(transcripts)

        summarizer = self._get_summarizer()
        available = await summarizer.is_available()
        if not available:
            logger.warning(f"Summarizer '{self._config.summarization_provider}' is not available")
            return None

        logger.info(f"Summarizing session {session_id} ({len(transcripts)} segments, {len(speakers)} speakers)")
        summary = await summarizer.summarize(formatted, speakers)

        # Persist to database
        await db.save_summary(
            session_id=session_id,
            executive_summary=summary.executive_summary,
            key_points=summary.key_points,
            action_items=[f"{a.description} (assignee: {a.assignee}, deadline: {a.deadline})" for a in summary.action_items],
            decisions=summary.decisions,
            next_steps=summary.next_steps,
            model_used=f"{self._config.summarization_provider}/{getattr(summarizer, 'model', '')}",
        )
        logger.info(f"Summary saved for session {session_id}")
        return summary

    async def check_availability(self) -> dict:
        """Check if the configured summarizer is reachable."""
        summarizer = self._get_summarizer()
        available = await summarizer.is_available()
        extra: dict = {}
        if isinstance(summarizer, OllamaSummarizer):
            extra["models"] = await summarizer.list_models()
        return {
            "provider": self._config.summarization_provider,
            "model": getattr(summarizer, "model", ""),
            "available": available,
            **extra,
        }
