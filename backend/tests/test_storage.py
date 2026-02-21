"""Tests for the OpenNode storage layer: database, export functions, and DataManager."""

from __future__ import annotations

import pytest
from datetime import datetime
from pathlib import Path


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def db(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Yield an initialised in-memory-ish Database for testing, then close it."""
    from opennode.storage.database import Database

    database = Database(tmp_path / "test.db")
    await database.initialize()
    yield database
    await database.close()


# ─── Database: Sessions ───────────────────────────────────────────────────────


async def test_create_and_get_session(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test Meeting")
    session = await db.get_session(session_id)
    assert session is not None
    assert session.title == "Test Meeting"
    assert session.status == "active"
    assert session.language == "auto"
    assert session.model_used == "parakeet"


async def test_create_session_custom_params(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session(
        "Custom Meeting", language="en", model_used="whisper", audio_source="microphone"
    )
    session = await db.get_session(session_id)
    assert session is not None
    assert session.language == "en"
    assert session.model_used == "whisper"
    assert session.audio_source == "microphone"


async def test_get_session_not_found(db) -> None:  # type: ignore[no-untyped-def]
    session = await db.get_session("non-existent-id")
    assert session is None


async def test_update_session(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Old Title")
    await db.update_session(session_id, title="New Title", status="completed")
    session = await db.get_session(session_id)
    assert session is not None
    assert session.title == "New Title"
    assert session.status == "completed"


async def test_end_session(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Meeting")
    await db.end_session(session_id, duration_ms=60000)
    session = await db.get_session(session_id)
    assert session is not None
    assert session.status == "completed"
    assert session.duration_ms == 60000
    assert session.ended_at is not None


async def test_delete_session(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("To Delete")
    await db.delete_session(session_id)
    session = await db.get_session(session_id)
    assert session is None


# ─── Database: Transcripts ────────────────────────────────────────────────────


async def test_add_and_get_transcripts(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(session_id, "Hello world", start_ms=0, end_ms=1000)
    transcripts = await db.get_transcripts(session_id)
    assert len(transcripts) == 1
    assert transcripts[0].text == "Hello world"
    assert transcripts[0].start_ms == 0
    assert transcripts[0].end_ms == 1000


async def test_add_transcript_with_speaker(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(
        session_id, "Good morning", speaker="Alice", start_ms=500, end_ms=2000, confidence=0.92
    )
    transcripts = await db.get_transcripts(session_id)
    assert transcripts[0].speaker == "Alice"
    assert transcripts[0].confidence == 0.92


async def test_partial_transcripts_excluded_by_default(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(session_id, "Final text", is_partial=False)
    await db.add_transcript(session_id, "Partial text", is_partial=True)
    transcripts = await db.get_transcripts(session_id, include_partials=False)
    assert len(transcripts) == 1
    assert transcripts[0].text == "Final text"


async def test_partial_transcripts_included_when_requested(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(session_id, "Final", is_partial=False)
    await db.add_transcript(session_id, "Partial", is_partial=True)
    transcripts = await db.get_transcripts(session_id, include_partials=True)
    assert len(transcripts) == 2


async def test_delete_partial_transcripts(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(session_id, "Final", is_partial=False)
    await db.add_transcript(session_id, "Partial 1", is_partial=True)
    await db.add_transcript(session_id, "Partial 2", is_partial=True)
    await db.delete_partial_transcripts(session_id)
    transcripts = await db.get_transcripts(session_id, include_partials=True)
    assert len(transcripts) == 1
    assert transcripts[0].text == "Final"


# ─── Database: Summaries ──────────────────────────────────────────────────────


async def test_save_and_get_summary(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.save_summary(session_id, "Great meeting", ["Point 1"], ["Action 1"], [], [])
    summary = await db.get_summary(session_id)
    assert summary is not None
    assert summary.executive_summary == "Great meeting"
    assert summary.key_points == ["Point 1"]
    assert summary.action_items == ["Action 1"]
    assert summary.decisions == []
    assert summary.next_steps == []


async def test_save_summary_upsert(db) -> None:  # type: ignore[no-untyped-def]
    """Saving a summary twice should overwrite, not create a duplicate."""
    session_id = await db.create_session("Test")
    await db.save_summary(session_id, "First summary", [], [], [], [])
    await db.save_summary(session_id, "Updated summary", ["Key point"], [], [], [])
    summary = await db.get_summary(session_id)
    assert summary is not None
    assert summary.executive_summary == "Updated summary"
    assert summary.key_points == ["Key point"]


async def test_get_summary_not_found(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    summary = await db.get_summary(session_id)
    assert summary is None


# ─── Database: Cascade delete ─────────────────────────────────────────────────


async def test_delete_session_cascades(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Test")
    await db.add_transcript(session_id, "Hello")
    await db.save_summary(session_id, "Summary", [], [], [], [])
    await db.delete_session(session_id)
    session = await db.get_session(session_id)
    assert session is None
    # Transcripts and summary should also be gone (cascade)
    transcripts = await db.get_transcripts(session_id)
    assert transcripts == []
    summary = await db.get_summary(session_id)
    assert summary is None


# ─── Database: List sessions ──────────────────────────────────────────────────


async def test_list_sessions(db) -> None:  # type: ignore[no-untyped-def]
    for i in range(5):
        await db.create_session(f"Meeting {i}")
    sessions = await db.list_sessions(limit=3)
    assert len(sessions) == 3


async def test_list_sessions_pagination(db) -> None:  # type: ignore[no-untyped-def]
    for i in range(5):
        await db.create_session(f"Meeting {i}")
    first_page = await db.list_sessions(limit=2, offset=0)
    second_page = await db.list_sessions(limit=2, offset=2)
    assert len(first_page) == 2
    assert len(second_page) == 2
    ids_first = {s.id for s in first_page}
    ids_second = {s.id for s in second_page}
    assert ids_first.isdisjoint(ids_second)


async def test_list_sessions_filter_by_status(db) -> None:  # type: ignore[no-untyped-def]
    s1 = await db.create_session("Active meeting")
    s2 = await db.create_session("Completed meeting")
    await db.end_session(s2, duration_ms=5000)

    active = await db.list_sessions(status="active")
    completed = await db.list_sessions(status="completed")

    active_ids = {s.id for s in active}
    completed_ids = {s.id for s in completed}

    assert s1 in active_ids
    assert s2 in completed_ids
    assert s2 not in active_ids


# ─── Database: Full session ───────────────────────────────────────────────────


async def test_get_full_session(db) -> None:  # type: ignore[no-untyped-def]
    session_id = await db.create_session("Full Test")
    await db.add_transcript(session_id, "Segment 1", start_ms=0, end_ms=1000)
    await db.add_transcript(session_id, "Segment 2", start_ms=1000, end_ms=2000)
    await db.save_summary(session_id, "Summary", ["Point"], ["Action"], [], [])

    full = await db.get_full_session(session_id)
    assert full is not None
    assert full.session.id == session_id
    assert len(full.transcripts) == 2
    assert full.summary is not None
    assert full.summary.executive_summary == "Summary"


async def test_get_full_session_not_found(db) -> None:  # type: ignore[no-untyped-def]
    full = await db.get_full_session("does-not-exist")
    assert full is None


# ─── Export: Markdown ─────────────────────────────────────────────────────────


def _make_full_session():  # type: ignore[no-untyped-def]
    """Helper to build a SessionWithTranscripts fixture for export tests."""
    from opennode.storage.models import (
        SessionRecord,
        SessionWithTranscripts,
        SpeakerRecord,
        SummaryRecord,
        TranscriptRecord,
    )

    session = SessionRecord(
        id="test-id",
        title="Test Meeting",
        created_at=datetime(2025, 1, 1, 10, 0),
        ended_at=None,
        duration_ms=3_600_000,
        language="en",
        model_used="parakeet",
        audio_source="system",
        audio_file_path=None,
        status="completed",
    )
    transcript = TranscriptRecord(
        id=1,
        session_id="test-id",
        text="Hello world",
        speaker="Speaker 1",
        start_ms=0,
        end_ms=1000,
        confidence=0.95,
        is_partial=False,
        created_at=datetime(2025, 1, 1, 10, 0, 1),
    )
    summary = SummaryRecord(
        id=1,
        session_id="test-id",
        executive_summary="This was a productive meeting.",
        key_points=["Point A", "Point B"],
        action_items=["Action 1"],
        decisions=["Decision X"],
        next_steps=["Follow up"],
        model_used="llama3.2",
        created_at=datetime(2025, 1, 1, 10, 30),
    )
    speaker = SpeakerRecord(
        id="spk-1",
        session_id="test-id",
        auto_label="SPEAKER_00",
        user_label="Speaker 1",
        color="#FF5733",
        total_duration_ms=30000,
    )
    return SessionWithTranscripts(
        session=session,
        transcripts=[transcript],
        summary=summary,
        speakers=[speaker],
    )


def test_export_markdown() -> None:
    from opennode.storage.export import export_markdown

    full = _make_full_session()
    md = export_markdown(full)
    assert "Test Meeting" in md
    assert "Hello world" in md
    assert "Speaker 1" in md
    assert "This was a productive meeting." in md
    assert "Point A" in md
    assert "Action 1" in md
    assert "Decision X" in md


def test_export_markdown_no_summary() -> None:
    from opennode.storage.export import export_markdown
    from opennode.storage.models import SessionRecord, SessionWithTranscripts, TranscriptRecord

    session = SessionRecord(
        id="s1", title="No Summary", created_at=datetime(2025, 1, 1), ended_at=None,
        duration_ms=None, language="en", model_used="parakeet", audio_source="system",
        audio_file_path=None, status="active",
    )
    transcript = TranscriptRecord(
        id=1, session_id="s1", text="Only text", speaker=None,
        start_ms=0, end_ms=500, confidence=1.0, is_partial=False,
        created_at=datetime(2025, 1, 1),
    )
    full = SessionWithTranscripts(session=session, transcripts=[transcript], summary=None, speakers=[])
    md = export_markdown(full)
    assert "No Summary" in md
    assert "Only text" in md
    # Summary section should not appear
    assert "## Summary" not in md


# ─── Export: SRT ─────────────────────────────────────────────────────────────


def test_export_srt() -> None:
    from opennode.storage.export import export_srt

    full = _make_full_session()
    srt = export_srt(full)
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:01,000" in srt
    assert "[Speaker 1] Hello world" in srt


def test_export_srt_empty() -> None:
    from opennode.storage.export import export_srt
    from opennode.storage.models import SessionRecord, SessionWithTranscripts

    session = SessionRecord(
        id="s1", title="Empty", created_at=datetime.now(), ended_at=None,
        duration_ms=None, language="en", model_used="parakeet", audio_source="system",
        audio_file_path=None, status="active",
    )
    full = SessionWithTranscripts(session=session, transcripts=[], summary=None, speakers=[])
    srt = export_srt(full)
    assert srt == ""


# ─── Export: JSON ─────────────────────────────────────────────────────────────


def test_export_json() -> None:
    from opennode.storage.export import export_json

    full = _make_full_session()
    data = export_json(full)
    assert data["session"]["title"] == "Test Meeting"
    assert len(data["transcripts"]) == 1
    assert data["transcripts"][0]["text"] == "Hello world"
    assert data["summary"] is not None
    assert data["summary"]["executive_summary"] == "This was a productive meeting."
    assert len(data["speakers"]) == 1


# ─── Export: Plain text ───────────────────────────────────────────────────────


def test_export_txt() -> None:
    from opennode.storage.export import export_txt

    full = _make_full_session()
    txt = export_txt(full)
    assert "TEST MEETING" in txt
    assert "Hello world" in txt
    assert "Speaker 1" in txt


# ─── Export: format helpers ───────────────────────────────────────────────────


def test_format_duration() -> None:
    from opennode.storage.export import format_duration

    assert format_duration(90_000) == "01:30"
    assert format_duration(3_661_000) == "01:01:01"
    assert format_duration(0) == "00:00"
    assert format_duration(59_999) == "00:59"
    assert format_duration(3_600_000) == "01:00:00"


def test_format_srt_time() -> None:
    from opennode.storage.export import format_srt_time

    assert format_srt_time(1_500) == "00:00:01,500"
    assert format_srt_time(61_234) == "00:01:01,234"
    assert format_srt_time(0) == "00:00:00,000"
    assert format_srt_time(3_661_000) == "01:01:01,000"


def test_format_timestamp() -> None:
    from opennode.storage.export import format_timestamp

    assert format_timestamp(0) == "[00:00:00]"
    assert format_timestamp(65_000) == "[00:01:05]"
    assert format_timestamp(3_600_000) == "[01:00:00]"


# ─── DataManager ─────────────────────────────────────────────────────────────


async def test_data_manager_initialize(tmp_path: Path) -> None:
    from opennode.storage.manager import DataManager

    dm = DataManager(str(tmp_path / "opennode"))
    await dm.initialize()

    assert dm.data_dir.exists()
    assert dm.audio_dir.exists()
    assert dm.models_dir.exists()
    assert dm.db_path.parent.exists()

    await dm.close()


async def test_data_manager_get_storage_usage(tmp_path: Path) -> None:
    from opennode.storage.manager import DataManager

    dm = DataManager(str(tmp_path / "opennode"))
    await dm.initialize()

    usage = dm.get_storage_usage()
    assert "audio_bytes" in usage
    assert "db_bytes" in usage
    assert "model_bytes" in usage
    assert "total_bytes" in usage
    assert usage["total_bytes"] >= 0

    await dm.close()


async def test_data_manager_cleanup_old_audio(tmp_path: Path) -> None:
    """cleanup_old_audio returns 0 when the audio directory is empty."""
    from opennode.storage.manager import DataManager

    dm = DataManager(str(tmp_path / "opennode"))
    await dm.initialize()

    deleted = dm.cleanup_old_audio(max_age_days=30)
    assert deleted == 0

    await dm.close()
