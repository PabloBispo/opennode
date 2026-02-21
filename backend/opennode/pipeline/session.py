"""Manages a single WebSocket transcription session."""
import asyncio
import base64
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import numpy as np
from fastapi import WebSocket
from loguru import logger

from ..asr.base import ASREngine, TranscriptionResult
from ..protocol import (
    PartialTranscriptMessage, FinalTranscriptMessage,
    StatusMessage, ControlMessage, CaptureConfig
)
from ..vad.silero import SILERO_AVAILABLE, VADResult
from ..vad.accumulator import SpeechAccumulator

# Thread pool for CPU-bound ASR inference
_asr_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asr_worker")


class TranscriptionSession:
    """Manages one real-time transcription session over a WebSocket."""

    def __init__(self, websocket: WebSocket, asr_engine: Optional[ASREngine], session_id: Optional[str] = None):
        self.websocket = websocket
        self.asr_engine = asr_engine
        self.session_id = session_id or str(uuid.uuid4())
        self.chunk_counter = 0
        self.is_active = False
        self.transcript_chunks: list[TranscriptionResult] = []

        # VAD and accumulator — gracefully skip if torch not available
        self._vad = None
        self._accumulator = SpeechAccumulator(
            min_speech_ms=250,
            max_speech_ms=30_000,
            silence_timeout_ms=500,
            partial_interval_ms=500,
        )

        if SILERO_AVAILABLE:
            try:
                from ..vad.silero import SileroVAD
                self._vad = SileroVAD()
            except Exception as e:
                logger.warning(f"Could not initialize SileroVAD: {e}")

    async def start(self, config: Optional[CaptureConfig] = None) -> None:
        """Start the session and send transcribing status."""
        self.is_active = True
        if self._vad:
            self._vad.reset()
        self._accumulator.reset()
        await self._send_status("transcribing")

    async def stop(self) -> None:
        """Stop the session and send ready status."""
        self.is_active = False
        await self._send_status("ready")

    async def pause(self) -> None:
        """Pause the session and send paused status."""
        self.is_active = False
        await self._send_status("paused")

    async def resume(self) -> None:
        """Resume the session and send transcribing status."""
        self.is_active = True
        await self._send_status("transcribing")

    async def process_audio(self, audio: np.ndarray, timestamp: int) -> None:
        """Route audio through VAD -> accumulator -> ASR."""
        if not self.is_active:
            return

        # --- With VAD ---
        if self._vad is not None:
            vad_result = self._vad.process_chunk(audio)

            complete_segment = self._accumulator.add_chunk(vad_result)
            if complete_segment is not None and self.asr_engine and self.asr_engine.is_loaded:
                result = await self._run_asr(complete_segment)
                if result:
                    await self._send_final(result)

            elif vad_result.is_speech:
                partial_audio = self._accumulator.get_partial()
                if partial_audio is not None and self.asr_engine and self.asr_engine.is_loaded:
                    result = await self._run_asr(partial_audio)
                    if result:
                        await self._send_partial(result)
        # --- Without VAD: send everything to ASR directly ---
        else:
            if self.asr_engine and self.asr_engine.is_loaded:
                result = await self._run_asr(audio)
                if result:
                    await self._send_final(result)

    async def _run_asr(self, audio: np.ndarray) -> Optional[TranscriptionResult]:
        """Run ASR inference in thread pool to avoid blocking the event loop."""
        if not self.asr_engine:
            return None
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                _asr_executor,
                lambda: asyncio.run(self.asr_engine.transcribe(audio))
            )
            return result
        except Exception as e:
            logger.error(f"ASR inference error: {e}")
            return None

    async def _send_partial(self, result: TranscriptionResult) -> None:
        """Send a partial transcript message over the WebSocket."""
        msg = PartialTranscriptMessage(
            text=result.text,
            chunk_id=self.chunk_counter,
            confidence=result.confidence,
            timestamp_ms=result.start_ms,
        )
        await self.websocket.send_text(msg.model_dump_json())

    async def _send_final(self, result: TranscriptionResult) -> None:
        """Send a final transcript message over the WebSocket."""
        self.chunk_counter += 1
        self.transcript_chunks.append(result)
        from ..protocol import WordTimestamp as WS_WordTimestamp
        words = [
            WS_WordTimestamp(word=w.word, start_ms=w.start_ms, end_ms=w.end_ms, confidence=w.confidence)
            for w in (result.words or [])
        ]
        msg = FinalTranscriptMessage(
            text=result.text,
            chunk_id=self.chunk_counter - 1,
            confidence=result.confidence,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
            words=words,
        )
        await self.websocket.send_text(msg.model_dump_json())

    async def _send_status(self, state: str) -> None:
        """Send a status message over the WebSocket."""
        from ..utils import check_gpu
        gpu = check_gpu()
        msg = StatusMessage(
            state=state,  # type: ignore[arg-type]
            model_loaded=bool(self.asr_engine and self.asr_engine.is_loaded),
            gpu_available=gpu["available"],
        )
        await self.websocket.send_text(msg.model_dump_json())

    async def cleanup(self) -> None:
        """Clean up session resources."""
        self.is_active = False
        logger.info(f"Session {self.session_id} cleaned up ({self.chunk_counter} chunks)")
