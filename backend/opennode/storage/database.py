"""Async SQLite database service for OpenNode."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from .models import (
    SessionRecord,
    SessionWithTranscripts,
    SpeakerRecord,
    SummaryRecord,
    TranscriptRecord,
)

# ─── DDL ─────────────────────────────────────────────────────────────────────

CREATE_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ended_at TEXT,
    duration_ms INTEGER,
    language TEXT DEFAULT 'auto',
    model_used TEXT DEFAULT 'parakeet',
    audio_source TEXT DEFAULT 'system',
    audio_file_path TEXT,
    status TEXT DEFAULT 'active'
);
"""

CREATE_TRANSCRIPTS_SQL = """
CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    speaker TEXT,
    start_ms INTEGER NOT NULL DEFAULT 0,
    end_ms INTEGER NOT NULL DEFAULT 0,
    confidence REAL DEFAULT 1.0,
    is_partial INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

CREATE_SUMMARIES_SQL = """
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    executive_summary TEXT,
    key_points TEXT DEFAULT '[]',
    action_items TEXT DEFAULT '[]',
    decisions TEXT DEFAULT '[]',
    next_steps TEXT DEFAULT '[]',
    model_used TEXT,
    created_at TEXT NOT NULL
);
"""

CREATE_SPEAKERS_SQL = """
CREATE TABLE IF NOT EXISTS speakers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    auto_label TEXT NOT NULL,
    user_label TEXT,
    color TEXT,
    total_duration_ms INTEGER DEFAULT 0
);
"""

_ALL_TABLES_SQL = (
    CREATE_SESSIONS_SQL
    + CREATE_TRANSCRIPTS_SQL
    + CREATE_SUMMARIES_SQL
    + CREATE_SPEAKERS_SQL
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string stored in SQLite, or return None."""
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _dt_str(dt: datetime) -> str:
    """Serialise a datetime to the ISO-8601 string used in the database."""
    return dt.isoformat()


def _row_to_session(row: aiosqlite.Row) -> SessionRecord:
    return SessionRecord(
        id=row["id"],
        title=row["title"],
        created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
        ended_at=_parse_dt(row["ended_at"]),
        duration_ms=row["duration_ms"],
        language=row["language"],
        model_used=row["model_used"],
        audio_source=row["audio_source"],
        audio_file_path=row["audio_file_path"],
        status=row["status"],
    )


def _row_to_transcript(row: aiosqlite.Row) -> TranscriptRecord:
    return TranscriptRecord(
        id=row["id"],
        session_id=row["session_id"],
        text=row["text"],
        speaker=row["speaker"],
        start_ms=row["start_ms"],
        end_ms=row["end_ms"],
        confidence=row["confidence"],
        is_partial=bool(row["is_partial"]),
        created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
    )


def _row_to_summary(row: aiosqlite.Row) -> SummaryRecord:
    return SummaryRecord(
        id=row["id"],
        session_id=row["session_id"],
        executive_summary=row["executive_summary"] or "",
        key_points=json.loads(row["key_points"] or "[]"),
        action_items=json.loads(row["action_items"] or "[]"),
        decisions=json.loads(row["decisions"] or "[]"),
        next_steps=json.loads(row["next_steps"] or "[]"),
        model_used=row["model_used"] or "",
        created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
    )


def _row_to_speaker(row: aiosqlite.Row) -> SpeakerRecord:
    return SpeakerRecord(
        id=row["id"],
        session_id=row["session_id"],
        auto_label=row["auto_label"],
        user_label=row["user_label"],
        color=row["color"],
        total_duration_ms=row["total_duration_ms"],
    )


# ─── Database class ───────────────────────────────────────────────────────────


class Database:
    """Async SQLite database service using aiosqlite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the database connection and configure pragmas."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

    async def initialize(self) -> None:
        """Create tables if they do not exist yet."""
        if not self._conn:
            await self.connect()
        assert self._conn is not None
        await self._conn.executescript(_ALL_TABLES_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ── Internal helper ────────────────────────────────────────────────────

    @property
    def _db(self) -> aiosqlite.Connection:
        """Return the active connection, raising if not yet initialised."""
        if self._conn is None:
            raise RuntimeError("Database not initialised — call initialize() first")
        return self._conn

    # ── Sessions ───────────────────────────────────────────────────────────

    async def create_session(
        self,
        title: str,
        language: str = "auto",
        model_used: str = "parakeet",
        audio_source: str = "system",
    ) -> str:
        """Insert a new session and return its UUID."""
        session_id = str(uuid.uuid4())
        now = _dt_str(datetime.utcnow())
        await self._db.execute(
            """
            INSERT INTO sessions (id, title, created_at, language, model_used, audio_source, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            """,
            (session_id, title, now, language, model_used, audio_source),
        )
        await self._db.commit()
        return session_id

    async def update_session(self, session_id: str, **kwargs: object) -> None:
        """Update arbitrary columns on a session row.

        Only known column names are accepted to prevent SQL injection.
        """
        allowed = {
            "title",
            "ended_at",
            "duration_ms",
            "language",
            "model_used",
            "audio_source",
            "audio_file_path",
            "status",
        }
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        if not filtered:
            return
        set_clause = ", ".join(f"{col} = ?" for col in filtered)
        values = list(filtered.values()) + [session_id]
        await self._db.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        await self._db.commit()

    async def end_session(self, session_id: str, duration_ms: int) -> None:
        """Mark a session as completed and record its end time and duration."""
        now = _dt_str(datetime.utcnow())
        await self._db.execute(
            "UPDATE sessions SET ended_at = ?, duration_ms = ?, status = 'completed' WHERE id = ?",
            (now, duration_ms, session_id),
        )
        await self._db.commit()

    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Fetch a single session by its ID."""
        async with self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_session(row)

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> list[SessionRecord]:
        """Return a page of sessions ordered by creation time (newest first)."""
        if status is not None:
            async with self._db.execute(
                "SELECT * FROM sessions WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with self._db.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_session(r) for r in rows]

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all its related rows (cascade)."""
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()

    # ── Transcripts ────────────────────────────────────────────────────────

    async def add_transcript(
        self,
        session_id: str,
        text: str,
        speaker: Optional[str] = None,
        start_ms: int = 0,
        end_ms: int = 0,
        confidence: float = 1.0,
        is_partial: bool = False,
    ) -> int:
        """Insert a transcript segment and return its auto-incremented ID."""
        now = _dt_str(datetime.utcnow())
        async with self._db.execute(
            """
            INSERT INTO transcripts
                (session_id, text, speaker, start_ms, end_ms, confidence, is_partial, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, text, speaker, start_ms, end_ms, confidence, int(is_partial), now),
        ) as cursor:
            row_id = cursor.lastrowid
        await self._db.commit()
        return row_id  # type: ignore[return-value]

    async def get_transcripts(
        self,
        session_id: str,
        include_partials: bool = False,
    ) -> list[TranscriptRecord]:
        """Fetch all final (and optionally partial) transcript segments for a session."""
        if include_partials:
            async with self._db.execute(
                "SELECT * FROM transcripts WHERE session_id = ? ORDER BY start_ms, id",
                (session_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with self._db.execute(
                "SELECT * FROM transcripts WHERE session_id = ? AND is_partial = 0 ORDER BY start_ms, id",
                (session_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_transcript(r) for r in rows]

    async def delete_partial_transcripts(self, session_id: str) -> None:
        """Remove all partial transcript rows for a session."""
        await self._db.execute(
            "DELETE FROM transcripts WHERE session_id = ? AND is_partial = 1",
            (session_id,),
        )
        await self._db.commit()

    # ── Summaries ──────────────────────────────────────────────────────────

    async def save_summary(
        self,
        session_id: str,
        executive_summary: str,
        key_points: list[str],
        action_items: list[str],
        decisions: Optional[list[str]] = None,
        next_steps: Optional[list[str]] = None,
        model_used: str = "",
    ) -> None:
        """Upsert the summary for a session (one summary per session)."""
        now = _dt_str(datetime.utcnow())
        await self._db.execute(
            """
            INSERT INTO summaries
                (session_id, executive_summary, key_points, action_items, decisions,
                 next_steps, model_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                executive_summary = excluded.executive_summary,
                key_points = excluded.key_points,
                action_items = excluded.action_items,
                decisions = excluded.decisions,
                next_steps = excluded.next_steps,
                model_used = excluded.model_used
            """,
            (
                session_id,
                executive_summary,
                json.dumps(key_points),
                json.dumps(action_items),
                json.dumps(decisions or []),
                json.dumps(next_steps or []),
                model_used,
                now,
            ),
        )
        await self._db.commit()

    async def get_summary(self, session_id: str) -> Optional[SummaryRecord]:
        """Fetch the summary for a session, or None if not yet generated."""
        async with self._db.execute(
            "SELECT * FROM summaries WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_summary(row)

    # ── Speakers ───────────────────────────────────────────────────────────

    async def upsert_speaker(
        self,
        session_id: str,
        auto_label: str,
        user_label: Optional[str] = None,
        color: Optional[str] = None,
        total_duration_ms: int = 0,
    ) -> str:
        """Insert or update a speaker record. Returns the speaker UUID."""
        # Check if already exists for this session/label combination
        async with self._db.execute(
            "SELECT id FROM speakers WHERE session_id = ? AND auto_label = ?",
            (session_id, auto_label),
        ) as cursor:
            row = await cursor.fetchone()

        if row is not None:
            speaker_id: str = row["id"]
            await self._db.execute(
                """
                UPDATE speakers
                SET user_label = COALESCE(?, user_label),
                    color = COALESCE(?, color),
                    total_duration_ms = ?
                WHERE id = ?
                """,
                (user_label, color, total_duration_ms, speaker_id),
            )
        else:
            speaker_id = str(uuid.uuid4())
            await self._db.execute(
                """
                INSERT INTO speakers (id, session_id, auto_label, user_label, color, total_duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (speaker_id, session_id, auto_label, user_label, color, total_duration_ms),
            )
        await self._db.commit()
        return speaker_id

    async def get_speakers(self, session_id: str) -> list[SpeakerRecord]:
        """Fetch all speakers for a session."""
        async with self._db.execute(
            "SELECT * FROM speakers WHERE session_id = ? ORDER BY auto_label",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_speaker(r) for r in rows]

    # ── Full session ───────────────────────────────────────────────────────

    async def get_full_session(self, session_id: str) -> Optional[SessionWithTranscripts]:
        """Return a session with all its transcripts, summary, and speakers."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        transcripts = await self.get_transcripts(session_id, include_partials=False)
        summary = await self.get_summary(session_id)
        speakers = await self.get_speakers(session_id)
        return SessionWithTranscripts(
            session=session,
            transcripts=transcripts,
            summary=summary,
            speakers=speakers,
        )
