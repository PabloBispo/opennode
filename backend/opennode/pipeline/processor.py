"""Audio pipeline processor orchestrating VAD -> ASR flow.

This is a scaffold implementation. Full WebSocket integration will be
completed in Task 04.
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

import numpy as np


class AudioProcessor:
    """Orchestrates the VAD -> ASR pipeline.

    Receives raw PCM audio chunks from the WebSocket, runs Voice Activity
    Detection, accumulates speech segments, and dispatches them to the ASR
    engine.

    This scaffold wires up the structural pieces (config, callbacks, lifecycle)
    and provides a ``process_chunk`` entry point. Full VAD/ASR integration
    will be completed in Task 04.

    Args:
        config: OpenNode ``Settings`` instance.
        on_partial: Async callback invoked with partial transcription text.
        on_final: Async callback invoked with the final transcription text.

    Example:
        processor = AudioProcessor(config, on_partial=..., on_final=...)
        await processor.start()
        await processor.process_chunk(pcm_bytes)
        await processor.stop()
    """

    def __init__(
        self,
        config,
        on_partial: Optional[Callable] = None,
        on_final: Optional[Callable] = None,
    ) -> None:
        self.config = config
        self.on_partial: Optional[Callable] = on_partial
        self.on_final: Optional[Callable] = on_final
        self._running = False

    async def start(self) -> None:
        """Start the processor and prepare internal state."""
        self._running = True

    async def stop(self) -> None:
        """Stop the processor and release resources."""
        self._running = False

    async def process_chunk(self, audio_bytes: bytes) -> None:
        """Accept a raw PCM chunk (16-bit, 16kHz, mono) and route through the pipeline.

        Converts the raw bytes to a normalized float32 numpy array, then
        passes the audio through VAD and the accumulator. ASR dispatch will
        be wired in Task 04.

        Args:
            audio_bytes: Raw little-endian int16 PCM audio bytes.
        """
        if not self._running:
            return

        # Convert bytes -> float32 numpy array, normalised to [-1.0, 1.0]
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # Pipeline: VAD -> accumulator -> ASR (stub for now)
        # Full implementation in Task 04.
        _ = audio
