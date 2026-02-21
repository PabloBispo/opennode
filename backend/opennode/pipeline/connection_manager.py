"""Manages multiple concurrent WebSocket sessions."""
from fastapi import WebSocket
from loguru import logger
from typing import Optional
from ..asr.base import ASREngine
from .session import TranscriptionSession


class ConnectionManager:
    """Manages multiple concurrent WebSocket transcription sessions."""

    def __init__(self):
        self._sessions: dict[str, TranscriptionSession] = {}

    async def connect(self, websocket: WebSocket, asr_engine: Optional[ASREngine] = None) -> TranscriptionSession:
        """Create a new session and register it."""
        session = TranscriptionSession(websocket, asr_engine)
        self._sessions[session.session_id] = session
        logger.info(f"New session: {session.session_id} (total: {len(self._sessions)})")
        return session

    async def disconnect(self, session_id: str) -> None:
        """Clean up and remove a session by ID."""
        if session_id in self._sessions:
            await self._sessions[session_id].cleanup()
            del self._sessions[session_id]
            logger.info(f"Session disconnected: {session_id} (remaining: {len(self._sessions)})")

    @property
    def active_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)
