"""faster-whisper ASR engine (CPU/GPU fallback)."""

from __future__ import annotations

from typing import Any, Iterator, Optional

import numpy as np
from loguru import logger

from .base import ASREngine, TranscriptionResult, WordTimestamp

try:
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class WhisperEngine(ASREngine):
    """ASR engine backed by faster-whisper (CTranslate2-optimised Whisper).

    This engine works on both GPU and CPU. The default model is ``large-v3``
    with float16 compute type, which requires a CUDA GPU. On CPU, set
    ``compute_type="int8"`` for acceptable performance.

    faster-whisper must be installed via:
        pip install 'opennode-backend[whisper]'
    """

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "float16",
        language: Optional[str] = None,
        beam_size: int = 5,
        word_timestamps: bool = True,
    ) -> None:
        """Initialise the engine configuration (does not load the model yet).

        Args:
            model_size: One of the Whisper model sizes (``tiny``, ``base``,
                ``small``, ``medium``, ``large-v2``, ``large-v3``, …).
            device: ``"cuda"``, ``"cpu"``, or ``"auto"`` (auto-detect).
            compute_type: CTranslate2 quantisation type.  Use ``"float16"``
                on GPU or ``"int8"`` / ``"int8_float16"`` on CPU.
            language: ISO 639-1 language code or *None* for auto-detection.
            beam_size: Beam search width during decoding.
            word_timestamps: Whether to request word-level timestamps.
        """
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._beam_size = beam_size
        self._word_timestamps = word_timestamps
        self._model: Any = None

    # ------------------------------------------------------------------
    # ASREngine interface
    # ------------------------------------------------------------------

    async def load_model(self) -> None:
        """Download (if needed) and load the Whisper model.

        Raises:
            ImportError: If faster-whisper is not installed.
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. "
                "Install it with: pip install 'opennode-backend[whisper]'"
            )

        if self._model is not None:
            logger.debug("Whisper model is already loaded — skipping.")
            return

        resolved_device = self._resolve_device()
        compute_type = self._resolve_compute_type(resolved_device)

        logger.info(
            f"Loading Whisper '{self._model_size}' on '{resolved_device}' "
            f"with compute_type='{compute_type}' …"
        )

        self._model = WhisperModel(
            self._model_size,
            device=resolved_device,
            compute_type=compute_type,
        )
        logger.info("Whisper model loaded successfully.")

    async def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe a complete audio segment.

        Args:
            audio: 1-D float32 numpy array at *sample_rate* Hz.
            sample_rate: Sample rate in Hz (faster-whisper resamples internally).

        Returns:
            TranscriptionResult with text and word-level timestamps.
        """
        self._require_loaded()

        # faster-whisper expects float32 at 16 kHz.
        audio_f32 = audio.astype(np.float32)

        segments_iter, info = self._model.transcribe(
            audio_f32,
            language=self._language,
            beam_size=self._beam_size,
            word_timestamps=self._word_timestamps,
        )

        segments = list(segments_iter)

        if not segments:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=info.language if info else "en",
                start_ms=0,
                end_ms=int(len(audio) / sample_rate * 1000),
            )

        full_text = " ".join(seg.text.strip() for seg in segments)
        all_words: list[WordTimestamp] = []
        for seg in segments:
            all_words.extend(self._segment_words(seg))

        start_ms = int(segments[0].start * 1000)
        end_ms = int(segments[-1].end * 1000)

        # Average log-probability → probability as a rough confidence score.
        avg_log_prob = sum(
            getattr(seg, "avg_logprob", 0.0) for seg in segments
        ) / len(segments)
        confidence = float(np.exp(avg_log_prob))

        return TranscriptionResult(
            text=full_text.strip(),
            confidence=min(max(confidence, 0.0), 1.0),
            language=info.language if info else "en",
            start_ms=start_ms,
            end_ms=end_ms,
            words=all_words,
        )

    async def transcribe_stream(
        self, audio_chunk: np.ndarray
    ) -> TranscriptionResult:
        """Transcribe an audio chunk in streaming mode.

        faster-whisper does not have a native streaming API, so this method
        performs a full transcription on each chunk and marks the result as
        partial. Callers should accumulate results until the end of a VAD
        segment.

        Args:
            audio_chunk: 1-D float32 numpy array (one VAD chunk).

        Returns:
            Partial TranscriptionResult for the chunk.
        """
        result = await self.transcribe(audio_chunk)
        result.is_partial = True
        return result

    def unload_model(self) -> None:
        """Release the faster-whisper model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model unloaded.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def supports_streaming(self) -> bool:
        # Supported via chunk-by-chunk full transcription.
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_device(self) -> str:
        """Resolve 'auto' to an actual device string."""
        if self._device != "auto":
            return self._device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _resolve_compute_type(self, device: str) -> str:
        """Return a safe compute type for the given device.

        On CPU, float16 is not supported; fall back to int8.
        """
        if self._compute_type != "float16":
            return self._compute_type
        return self._compute_type if device == "cuda" else "int8"

    def _require_loaded(self) -> None:
        """Raise RuntimeError if the model has not been loaded."""
        if self._model is None:
            raise RuntimeError(
                "Whisper model is not loaded. Call load_model() first."
            )

    def _segment_words(self, segment: Any) -> list[WordTimestamp]:
        """Convert a faster-whisper segment's words to WordTimestamp objects.

        Args:
            segment: A faster-whisper ``Segment`` named tuple.

        Returns:
            List of WordTimestamp objects (empty if word timestamps unavailable).
        """
        words: list[WordTimestamp] = []
        raw_words = getattr(segment, "words", None)
        if not raw_words:
            return words

        for w in raw_words:
            words.append(
                WordTimestamp(
                    word=w.word.strip(),
                    start_ms=int(w.start * 1000),
                    end_ms=int(w.end * 1000),
                    confidence=float(getattr(w, "probability", 1.0)),
                )
            )
        return words
