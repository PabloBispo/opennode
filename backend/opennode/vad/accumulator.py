"""Speech accumulator for collecting VAD-processed audio chunks into utterances."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from .silero import VADResult


class SpeechAccumulator:
    """Accumulates VAD-processed audio chunks and emits complete utterances.

    An utterance is considered complete when:
    - Silence is detected after speech and ``silence_timeout_ms`` has elapsed
      since the last speech chunk was received.
    - OR the accumulated speech reaches ``max_speech_ms``.

    During continuous speech, ``get_partial()`` can be polled to emit partial
    results every ``partial_interval_ms`` for low-latency transcription.

    Example:
        acc = SpeechAccumulator()
        for chunk in audio_stream:
            vad_result = vad.process_chunk(chunk)
            utterance = acc.add_chunk(vad_result)
            if utterance is not None:
                send_to_asr(utterance)
            partial = acc.get_partial()
            if partial is not None:
                send_partial_to_asr(partial)
    """

    def __init__(
        self,
        min_speech_ms: int = 250,
        max_speech_ms: int = 30_000,
        silence_timeout_ms: int = 500,
        partial_interval_ms: int = 500,
        sample_rate: int = 16_000,
    ) -> None:
        """Initialize the accumulator.

        Args:
            min_speech_ms: Minimum speech duration before a segment can be emitted.
            max_speech_ms: Maximum speech duration before forcefully emitting.
            silence_timeout_ms: Duration of silence (since last speech chunk) required
                to complete an utterance.
            partial_interval_ms: Interval for emitting partial results during speech.
            sample_rate: Audio sample rate in Hz.
        """
        self.min_speech_ms = min_speech_ms
        self.max_speech_ms = max_speech_ms
        self.silence_timeout_ms = silence_timeout_ms
        self.partial_interval_ms = partial_interval_ms
        self.sample_rate = sample_rate

        self._chunks: list[np.ndarray] = []
        self._in_speech: bool = False
        self._speech_start_time: float = 0.0
        # Wall-clock time of the last speech chunk — silence timeout measured from here
        self._last_speech_time: float = 0.0
        self._last_partial_time: float = 0.0
        self._accumulated_ms_value: float = 0.0

    def add_chunk(self, vad_result: VADResult) -> Optional[np.ndarray]:
        """Add a VAD-processed chunk and detect utterance boundaries.

        Returns the complete utterance audio when an utterance ends, or None
        while still accumulating.

        Args:
            vad_result: VAD result for the current audio chunk.

        Returns:
            Concatenated float32 audio array when utterance is complete, else None.
        """
        chunk_ms = (len(vad_result.audio) / self.sample_rate) * 1000.0
        now = time.monotonic()

        if vad_result.is_speech:
            if not self._in_speech:
                # Transition: silence -> speech — start a new utterance
                self._in_speech = True
                self._speech_start_time = now
                self._last_partial_time = now
                self._chunks = []
                self._accumulated_ms_value = 0.0

            self._chunks.append(vad_result.audio)
            self._accumulated_ms_value += chunk_ms
            self._last_speech_time = now

            # Force emit if max speech duration reached
            if self._accumulated_ms_value >= self.max_speech_ms:
                return self._emit()

        else:
            # Non-speech chunk
            if self._in_speech:
                # Collect trailing context
                self._chunks.append(vad_result.audio)
                self._accumulated_ms_value += chunk_ms

                silence_elapsed_ms = (now - self._last_speech_time) * 1000.0
                if silence_elapsed_ms >= self.silence_timeout_ms:
                    # Enough silence elapsed — emit if we accumulated enough speech
                    if self._accumulated_ms_value >= self.min_speech_ms:
                        return self._emit()
                    else:
                        # Too short — discard
                        self._reset_state()

        return None

    def get_partial(self) -> Optional[np.ndarray]:
        """Return current accumulated audio for partial transcription.

        Returns the accumulated audio if ``partial_interval_ms`` has elapsed
        since the last partial emission, or None otherwise.

        Returns:
            Float32 numpy array of accumulated audio, or None.
        """
        if not self._in_speech or not self._chunks:
            return None

        now = time.monotonic()
        elapsed_ms = (now - self._last_partial_time) * 1000.0
        if elapsed_ms >= self.partial_interval_ms:
            self._last_partial_time = now
            return np.concatenate(self._chunks)

        return None

    def reset(self) -> None:
        """Reset accumulator state. Call at session start/stop."""
        self._reset_state()

    def _emit(self) -> np.ndarray:
        """Concatenate all accumulated chunks and reset state."""
        result = np.concatenate(self._chunks)
        self._reset_state()
        return result

    def _reset_state(self) -> None:
        """Internal state reset helper."""
        self._chunks = []
        self._in_speech = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._last_partial_time = 0.0
        self._accumulated_ms_value = 0.0

    @property
    def is_in_speech(self) -> bool:
        """True if currently inside a speech segment."""
        return self._in_speech

    @property
    def accumulated_ms(self) -> float:
        """Total accumulated audio duration in milliseconds."""
        return self._accumulated_ms_value
