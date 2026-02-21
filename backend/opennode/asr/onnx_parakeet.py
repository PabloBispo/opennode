"""ONNX Parakeet ASR engine for CPU-only / quantised inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np
from loguru import logger

from .base import ASREngine, TranscriptionResult, WordTimestamp

try:
    from onnx_asr import Parakeet  # type: ignore[import-untyped]

    ONNX_ASR_AVAILABLE = True
except ImportError:
    ONNX_ASR_AVAILABLE = False

DEFAULT_CACHE_DIR = Path("~/.opennode/models").expanduser()
# INT8 quantised ONNX model — approx 640 MB on disk.
ONNX_MODEL_ID = "nvidia/parakeet-tdt-0.6b-v3"


class OnnxParakeetEngine(ASREngine):
    """CPU-only ASR engine using an INT8-quantised ONNX export of Parakeet.

    This engine is the preferred fallback for machines without a CUDA GPU.
    It uses the ``onnx-asr`` library which bundles the ONNX runtime and
    model weights (~640 MB after quantisation).

    Install via:
        pip install 'opennode-backend[cpu]'
    """

    def __init__(
        self,
        model_id: str = ONNX_MODEL_ID,
        cache_dir: Optional[Path] = None,
    ) -> None:
        """Initialise the engine (does not load the model yet).

        Args:
            model_id: HuggingFace / Hub model identifier for the ONNX export.
            cache_dir: Directory where model files will be cached.
        """
        self._model_id = model_id
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._model: Any = None
        self._streaming_buffer: list[np.ndarray] = []

    # ------------------------------------------------------------------
    # ASREngine interface
    # ------------------------------------------------------------------

    async def load_model(self) -> None:
        """Download (if needed) and load the ONNX Parakeet model.

        Raises:
            ImportError: If onnx-asr is not installed.
        """
        if not ONNX_ASR_AVAILABLE:
            raise ImportError(
                "onnx-asr is not installed. "
                "Install it with: pip install 'opennode-backend[cpu]'"
            )

        if self._model is not None:
            logger.debug("ONNX Parakeet model is already loaded — skipping.")
            return

        self._cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Loading ONNX Parakeet model '{self._model_id}' (CPU, INT8) …"
        )

        # onnx-asr handles model download and caching automatically.
        self._model = Parakeet(  # type: ignore[call-arg]
            model=self._model_id,
            cache_dir=str(self._cache_dir),
        )
        logger.info("ONNX Parakeet model loaded successfully.")

    async def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe a complete audio segment.

        Args:
            audio: 1-D float32 numpy array at *sample_rate* Hz.
            sample_rate: Sample rate in Hz (must be 16 000 for Parakeet).

        Returns:
            TranscriptionResult with text and word-level timestamps.
        """
        self._require_loaded()

        audio_f32 = audio.astype(np.float32)
        duration_ms = int(len(audio_f32) / sample_rate * 1000)

        # onnx-asr API: model(audio) → transcription string or result object.
        raw = self._model(audio_f32)

        text, words = self._parse_result(raw, duration_ms)

        return TranscriptionResult(
            text=text,
            confidence=1.0,
            language="en",
            start_ms=0,
            end_ms=duration_ms,
            words=words,
        )

    async def transcribe_stream(
        self, audio_chunk: np.ndarray
    ) -> TranscriptionResult:
        """Accumulate a chunk and transcribe the full buffer.

        ONNX Parakeet does not have a native streaming mode; chunks are
        accumulated and a full pass is run on each call.

        Args:
            audio_chunk: 1-D float32 numpy array (one VAD chunk).

        Returns:
            Partial TranscriptionResult for the accumulated audio.
        """
        self._require_loaded()
        self._streaming_buffer.append(audio_chunk)
        combined = np.concatenate(self._streaming_buffer)

        result = await self.transcribe(combined)
        result.is_partial = True
        return result

    def unload_model(self) -> None:
        """Release the ONNX model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            self._streaming_buffer.clear()
            logger.info("ONNX Parakeet model unloaded.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def supports_streaming(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_loaded(self) -> None:
        """Raise RuntimeError if the model has not been loaded."""
        if self._model is None:
            raise RuntimeError(
                "ONNX Parakeet model is not loaded. Call load_model() first."
            )

    def _parse_result(
        self, raw: Any, duration_ms: int
    ) -> tuple[str, list[WordTimestamp]]:
        """Parse the onnx-asr output into text and word timestamps.

        onnx-asr may return a plain string or a richer object depending on
        the version. This method handles both cases gracefully.

        Args:
            raw: Return value of ``self._model(audio)``.
            duration_ms: Total audio duration in milliseconds (used as
                fallback end timestamp when the model provides none).

        Returns:
            Tuple of (text, list[WordTimestamp]).
        """
        words: list[WordTimestamp] = []

        if isinstance(raw, str):
            return raw.strip(), words

        # Try to extract structured output (text + word timestamps).
        text = ""
        try:
            text = str(getattr(raw, "text", raw)).strip()
            raw_words = getattr(raw, "words", None) or []
            for w in raw_words:
                words.append(
                    WordTimestamp(
                        word=str(getattr(w, "word", "")).strip(),
                        start_ms=int(getattr(w, "start_ms", 0)),
                        end_ms=int(getattr(w, "end_ms", duration_ms)),
                        confidence=float(getattr(w, "confidence", 1.0)),
                    )
                )
        except Exception:
            text = str(raw).strip()

        return text, words
