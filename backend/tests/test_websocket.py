"""Tests for the WebSocket transcription endpoint and session management."""

import pytest
import json
import base64
import numpy as np
from httpx import AsyncClient, ASGITransport
from opennode.server import app


@pytest.mark.asyncio
async def test_status_endpoint():
    """GET /api/status should return expected fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert "active_sessions" in data
    assert "model_loaded" in data


@pytest.mark.asyncio
async def test_websocket_accepts_connection():
    """WebSocket connection should be accepted and return initial 'ready' status."""
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/transcribe") as ws:
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "status"
        assert msg["state"] == "ready"


@pytest.mark.asyncio
async def test_websocket_control_start_stop():
    """Control start/stop messages should transition session state correctly."""
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/transcribe") as ws:
        ws.receive_text()  # initial status
        ws.send_text(json.dumps({"type": "control", "action": "start", "session_id": "test"}))
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "status"
        assert msg["state"] == "transcribing"
        ws.send_text(json.dumps({"type": "control", "action": "stop", "session_id": "test"}))
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "status"
        assert msg["state"] == "ready"


@pytest.mark.asyncio
async def test_websocket_audio_chunk_no_crash():
    """Sending an audio chunk when no ASR is loaded should not crash."""
    from starlette.testclient import TestClient
    client = TestClient(app)
    silence = np.zeros(512, dtype=np.int16)
    audio_b64 = base64.b64encode(silence.tobytes()).decode()
    with client.websocket_connect("/ws/transcribe") as ws:
        ws.receive_text()  # initial status
        ws.send_text(json.dumps({"type": "control", "action": "start", "session_id": "test"}))
        ws.receive_text()  # transcribing status
        ws.send_text(json.dumps({"type": "audio_chunk", "data": audio_b64, "timestamp": 0, "session_id": "test"}))
        # No response expected for silence — just verify no exception


@pytest.mark.asyncio
async def test_websocket_invalid_json():
    """Sending invalid JSON should not crash the server."""
    from starlette.testclient import TestClient
    client = TestClient(app)
    with client.websocket_connect("/ws/transcribe") as ws:
        ws.receive_text()  # initial status
        ws.send_text("not valid json")
        # Server should log warning and continue


def test_transcription_session_init():
    """TranscriptionSession can be created without a real WebSocket."""
    from opennode.pipeline.session import TranscriptionSession
    # Should not raise even without VAD/ASR
    session = TranscriptionSession(websocket=None, asr_engine=None)  # type: ignore
    assert session.session_id is not None
    assert not session.is_active
    assert session.chunk_counter == 0
