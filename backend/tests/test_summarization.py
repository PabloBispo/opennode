import pytest
from unittest.mock import AsyncMock, patch

def test_meeting_summary_defaults():
    from opennode.summarization import MeetingSummary
    s = MeetingSummary(executive_summary="Test meeting")
    assert s.key_points == []
    assert s.action_items == []
    assert s.decisions == []

def test_action_item_fields():
    from opennode.summarization import ActionItem
    a = ActionItem(description="Fix bug", assignee="Alice", deadline="Friday")
    assert a.description == "Fix bug"
    assert a.assignee == "Alice"

def test_format_transcript_basic():
    from opennode.summarization import format_transcript_for_summary
    from opennode.storage.models import TranscriptRecord
    from datetime import datetime
    records = [
        TranscriptRecord(id=1, session_id="s1", text="Hello world",
                        speaker="SPEAKER_00", start_ms=0, end_ms=1000,
                        confidence=0.9, is_partial=False, created_at=datetime.now()),
        TranscriptRecord(id=2, session_id="s1", text="How are you",
                        speaker="SPEAKER_01", start_ms=2000, end_ms=3000,
                        confidence=0.9, is_partial=False, created_at=datetime.now()),
    ]
    formatted = format_transcript_for_summary(records)
    assert "Hello world" in formatted
    assert "SPEAKER_00" in formatted
    assert "How are you" in formatted

def test_build_speaker_list():
    from opennode.summarization import build_speaker_list
    from opennode.storage.models import TranscriptRecord
    from datetime import datetime
    records = [
        TranscriptRecord(id=1, session_id="s1", text="Hello", speaker="Alice",
                        start_ms=0, end_ms=500, confidence=0.9, is_partial=False, created_at=datetime.now()),
        TranscriptRecord(id=2, session_id="s1", text="Hi", speaker="Bob",
                        start_ms=500, end_ms=1000, confidence=0.9, is_partial=False, created_at=datetime.now()),
        TranscriptRecord(id=3, session_id="s1", text="Yes", speaker="Alice",
                        start_ms=1000, end_ms=1500, confidence=0.9, is_partial=False, created_at=datetime.now()),
    ]
    speakers = build_speaker_list(records)
    assert speakers == ["Alice", "Bob"]  # unique, order preserved

def test_ollama_summarizer_not_available_without_server():
    """OllamaSummarizer.is_available() returns False when Ollama not running."""
    import asyncio
    from opennode.summarization import OllamaSummarizer
    s = OllamaSummarizer(base_url="http://localhost:19999")  # unlikely port
    result = asyncio.run(s.is_available())
    assert result is False

def test_api_summarizer_unavailable_without_key():
    import asyncio
    from opennode.summarization import APISummarizer
    s = APISummarizer(provider="openai", api_key="")
    result = asyncio.run(s.is_available())
    assert result is False

def test_api_summarizer_invalid_provider():
    from opennode.summarization import APISummarizer
    with pytest.raises(ValueError, match="Unsupported provider"):
        APISummarizer(provider="invalid", api_key="test")

def test_ollama_parse_response_valid_json():
    from opennode.summarization.summarizer import OllamaSummarizer
    s = OllamaSummarizer()
    raw = '{"executive_summary": "Good meeting", "key_points": ["Point 1"], "action_items": [{"description": "Do it", "assignee": "Bob", "deadline": null}], "decisions": ["Go ahead"], "next_steps": ["Follow up"]}'
    result = s._parse_response(raw)
    assert result.executive_summary == "Good meeting"
    assert result.key_points == ["Point 1"]
    assert len(result.action_items) == 1
    assert result.action_items[0].assignee == "Bob"

def test_ollama_parse_response_invalid_json():
    from opennode.summarization.summarizer import OllamaSummarizer
    s = OllamaSummarizer()
    result = s._parse_response("This is not JSON at all")
    assert isinstance(result.executive_summary, str)

def test_format_transcript_truncation():
    from opennode.summarization import format_transcript_for_summary
    from opennode.storage.models import TranscriptRecord
    from datetime import datetime
    # Create a very long transcript
    records = [
        TranscriptRecord(id=i, session_id="s1", text="x" * 1000, speaker="SPK",
                        start_ms=i*1000, end_ms=(i+1)*1000, confidence=0.9,
                        is_partial=False, created_at=datetime.now())
        for i in range(500)  # 500KB+
    ]
    result = format_transcript_for_summary(records, max_chars=10_000)
    assert len(result) <= 10_100  # allow small overhead for truncation message
