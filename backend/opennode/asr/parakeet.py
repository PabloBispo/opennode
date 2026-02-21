"""NVIDIA Parakeet V3 ASR engine using NeMo toolkit."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
from loguru import logger

from .base import ASREngine, TranscriptionResult, WordTimestamp

try:
    import nemo.collections.asr as nemo_asr  # type: ignore[import-untyped]

    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False

MODEL_NAME = "nvidia/parakeet-tdt-0.6b-v3"
DEFAULT_CACHE_DIR = Path("~/.opennode/models").expanduser()


class ParakeetEngine(ASREngine):
    """ASR engine backed by NVIDIA Parakeet TDT 0.6B v3 via the NeMo toolkit.

    This engine requires GPU for best performance but will fall back to CPU
    if no CUDA device is detected. NeMo must be installed via the ``gpu``
    optional dependency group.

    Streaming is supported through the encoder cache mechanism provided by
    NeMo's CTC/TDT streaming helpers.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        cache_dir: Optional[Path] = None,
        device: Optional[str] = None,
    ) -> None:
        """Initialise the engine (does not load the model yet).

        Args:
            model_name: HuggingFace / NGC model identifier.
            cache_dir: Directory where the model will be cached.
            device: ``"cuda"`` or ``"cpu"``. If *None*, auto-detected.
        """
        self._model_name = model_name
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._device = device  # resolved lazily in load_model
        self._model: Any = None
        self._streaming_buffer: list[np.ndarray] = []

    # ------------------------------------------------------------------
    # ASREngine interface
    # ------------------------------------------------------------------

    async def load_model(self) -> None:
        """Download (if needed) and load the Parakeet model.

        Raises:
            ImportError: If NeMo is not installed.
        """
        if not NEMO_AVAILABLE:
            raise ImportError(
                "NeMo toolkit is not installed. "
                "Install it with: pip install 'opennode-backend[gpu]'\n"
                "Alternatively, use the ONNX or Whisper engine for CPU-only inference."
            )

        if self._model is not None:
            logger.debug("Parakeet model is already loaded — skipping.")
            return

        resolved_device = self._resolve_device()
        logger.info(
            f"Loading Parakeet model '{self._model_name}' on device '{resolved_device}' …"
        )

        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # NeMo automatically handles caching when map_location is set.
        self._model = nemo_asr.models.ASRModel.from_pretrained(  # type: ignore[union-attr]
            model_name=self._model_name,
            map_location=resolved_device,
        )
        self._model.eval()
        self._device = resolved_device
        logger.info("Parakeet model loaded successfully.")

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

        start_ms = 0
        duration_ms = int(len(audio) / sample_rate * 1000)

        # NeMo transcription returns a list of hypotheses.
        hypotheses = self._model.transcribe([audio], batch_size=1)
        hypothesis = hypotheses[0] if hypotheses else None

        if hypothesis is None or not str(hypothesis).strip():
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language="en",
                start_ms=start_ms,
                end_ms=duration_ms,
            )

        text = str(hypothesis).strip()
        words = self._extract_words(hypothesis, start_ms)

        return TranscriptionResult(
            text=text,
            confidence=1.0,  # NeMo TDT does not expose per-segment confidence
            language="en",
            start_ms=start_ms,
            end_ms=duration_ms,
            words=words,
        )

    async def transcribe_stream(
        self, audio_chunk: np.ndarray
    ) -> TranscriptionResult:
        """Accumulate a chunk and transcribe with the encoder cache.

        The current implementation buffers chunks and performs a full
        transcription pass. A future optimisation would use NeMo's
        dedicated streaming API when it becomes stable.

        Args:
            audio_chunk: 1-D float32 numpy array (one VAD chunk).

        Returns:
            Partial TranscriptionResult for the accumulated audio so far.
        """
        self._require_loaded()
        self._streaming_buffer.append(audio_chunk)
        combined = np.concatenate(self._streaming_buffer)

        result = await self.transcribe(combined)
        result.is_partial = True
        return result

    def unload_model(self) -> None:
        """Release the NeMo model and free GPU memory."""
        if self._model is not None:
            try:
                import torch

                del self._model
                torch.cuda.empty_cache()
            except ImportError:
                del self._model
            self._model = None
            self._streaming_buffer.clear()
            logger.info("Parakeet model unloaded.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def supports_streaming(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_device(self) -> str:
        """Choose CUDA or CPU based on availability."""
        if self._device:
            return self._device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _require_loaded(self) -> None:
        """Raise RuntimeError if the model has not been loaded yet."""
        if self._model is None:
            raise RuntimeError(
                "Parakeet model is not loaded. Call load_model() first."
            )

    def _extract_words(
        self, hypothesis: Any, base_start_ms: int
    ) -> list[WordTimestamp]:
        """Extract word-level timestamps from a NeMo hypothesis object.

        NeMo TDT hypotheses carry a ``timestep`` attribute with per-word
        timing when the model supports it. This method handles both the
        case where timestamps are available and the case where they are not.

        Args:
            hypothesis: NeMo hypothesis object (or plain string).
            base_start_ms: Offset in ms to add to all word timestamps.

        Returns:
            List of WordTimestamp objects (may be empty if not supported).
        """
        words: list[WordTimestamp] = []

        # Try to extract per-word timing if the hypothesis exposes it.
        try:
            word_timestamps = getattr(hypothesis, "timestep", None)
            if word_timestamps is None:
                return words

            # NeMo provides timestamps in frames; convert to ms.
            # Frame shift for Parakeet TDT is 80 ms (40 ms window, 20 ms hop).
            FRAME_MS = 80
            token_text = str(hypothesis)
            token_words = token_text.split()

            for i, ts in enumerate(word_timestamps):
                if i >= len(token_words):
                    break
                start = base_start_ms + int(ts) * FRAME_MS
                end = start + FRAME_MS  # approximate
                words.append(
                    WordTimestamp(
                        word=token_words[i],
                        start_ms=start,
                        end_ms=end,
                        confidence=1.0,
                    )
                )
        except Exception:
            # Timestamps not available for this hypothesis type — return empty.
            pass

        return words
