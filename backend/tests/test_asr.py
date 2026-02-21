"""Tests for the ASR engine abstraction layer.

These tests cover the interface, data models, and factory logic without
requiring any heavy ML dependencies (NeMo, faster-whisper, onnx-asr) to be
installed.  All tests that touch the factory check graceful error handling
rather than actual model inference.
"""

from __future__ import annotations

import numpy as np
import pytest

from opennode.asr.base import ASREngine, TranscriptionResult, WordTimestamp
from opennode.asr.factory import create_asr_engine
from opennode.asr.onnx_parakeet import ONNX_ASR_AVAILABLE, OnnxParakeetEngine
from opennode.asr.parakeet import NEMO_AVAILABLE, ParakeetEngine
from opennode.asr.whisper import FASTER_WHISPER_AVAILABLE, WhisperEngine
from opennode.config import Settings


# ---------------------------------------------------------------------------
# Data-model tests
# ---------------------------------------------------------------------------


def test_transcription_result_defaults() -> None:
    """TranscriptionResult must initialise with an empty words list by default."""
    result = TranscriptionResult(
        text="hello world",
        confidence=0.95,
        language="en",
        start_ms=0,
        end_ms=1000,
    )

    assert result.text == "hello world"
    assert result.confidence == 0.95
    assert result.language == "en"
    assert result.start_ms == 0
    assert result.end_ms == 1000
    assert result.words == []
    assert result.is_partial is False


def test_transcription_result_with_words() -> None:
    """TranscriptionResult should store provided WordTimestamp objects."""
    words = [
        WordTimestamp(word="hello", start_ms=0, end_ms=400, confidence=0.9),
        WordTimestamp(word="world", start_ms=500, end_ms=900, confidence=0.85),
    ]
    result = TranscriptionResult(
        text="hello world",
        confidence=0.9,
        language="en",
        start_ms=0,
        end_ms=1000,
        words=words,
    )

    assert len(result.words) == 2
    assert result.words[0].word == "hello"
    assert result.words[1].word == "world"


def test_transcription_result_partial_flag() -> None:
    """is_partial must be settable to True."""
    result = TranscriptionResult(
        text="partia",
        confidence=0.5,
        language="en",
        start_ms=0,
        end_ms=200,
        is_partial=True,
    )
    assert result.is_partial is True


def test_word_timestamp_fields() -> None:
    """WordTimestamp should store all four fields correctly."""
    wt = WordTimestamp(word="meeting", start_ms=120, end_ms=580, confidence=0.97)

    assert wt.word == "meeting"
    assert wt.start_ms == 120
    assert wt.end_ms == 580
    assert wt.confidence == 0.97


def test_word_timestamp_zero_confidence() -> None:
    """WordTimestamp should accept a confidence of 0.0."""
    wt = WordTimestamp(word="uh", start_ms=0, end_ms=50, confidence=0.0)
    assert wt.confidence == 0.0


def test_transcription_result_independent_word_lists() -> None:
    """Two TranscriptionResult instances must not share the same words list."""
    r1 = TranscriptionResult(
        text="a", confidence=1.0, language="en", start_ms=0, end_ms=100
    )
    r2 = TranscriptionResult(
        text="b", confidence=1.0, language="en", start_ms=0, end_ms=100
    )
    r1.words.append(WordTimestamp(word="a", start_ms=0, end_ms=50, confidence=1.0))
    assert r2.words == [], "Mutable default should not be shared between instances"


# ---------------------------------------------------------------------------
# Abstract base class tests
# ---------------------------------------------------------------------------


def test_asr_engine_is_abstract() -> None:
    """ASREngine cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ASREngine()  # type: ignore[abstract]


class _ConcreteEngine(ASREngine):
    """Minimal concrete implementation for interface testing."""

    _loaded: bool = False

    async def load_model(self) -> None:
        self._loaded = True

    async def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> TranscriptionResult:
        return TranscriptionResult(
            text="test", confidence=1.0, language="en", start_ms=0, end_ms=100
        )

    async def transcribe_stream(
        self, audio_chunk: np.ndarray
    ) -> TranscriptionResult:
        result = await self.transcribe(audio_chunk)
        result.is_partial = True
        return result

    def unload_model(self) -> None:
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def supports_streaming(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_concrete_engine_load_and_unload() -> None:
    """A concrete engine should transition between loaded/unloaded states."""
    engine = _ConcreteEngine()
    assert not engine.is_loaded

    await engine.load_model()
    assert engine.is_loaded

    engine.unload_model()
    assert not engine.is_loaded


@pytest.mark.asyncio
async def test_concrete_engine_transcribe() -> None:
    """transcribe() should return a TranscriptionResult."""
    engine = _ConcreteEngine()
    await engine.load_model()

    audio = np.zeros(16000, dtype=np.float32)
    result = await engine.transcribe(audio)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "test"


@pytest.mark.asyncio
async def test_concrete_engine_transcribe_stream_is_partial() -> None:
    """transcribe_stream() should return a partial result."""
    engine = _ConcreteEngine()
    await engine.load_model()

    chunk = np.zeros(3200, dtype=np.float32)
    result = await engine.transcribe_stream(chunk)

    assert result.is_partial is True


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


def test_factory_raises_on_unknown_engine() -> None:
    """Factory should raise ValueError for an unrecognised engine name."""
    config = Settings(asr_engine="invalid")
    with pytest.raises(ValueError, match="Unknown ASR engine"):
        create_asr_engine(config)


def test_factory_raises_on_empty_engine_name() -> None:
    """Factory should raise ValueError when the engine name is empty."""
    config = Settings(asr_engine="")
    with pytest.raises(ValueError, match="Unknown ASR engine"):
        create_asr_engine(config)


def test_factory_returns_correct_type_for_whisper() -> None:
    """Factory with 'whisper' engine should return WhisperEngine or raise ImportError."""
    config = Settings(asr_engine="whisper")

    if FASTER_WHISPER_AVAILABLE:
        engine = create_asr_engine(config)
        assert isinstance(engine, WhisperEngine)
    else:
        with pytest.raises(ImportError, match="faster-whisper"):
            create_asr_engine(config)


def test_factory_returns_correct_type_for_onnx() -> None:
    """Factory with 'onnx' engine should return OnnxParakeetEngine or raise ImportError."""
    config = Settings(asr_engine="onnx")

    if ONNX_ASR_AVAILABLE:
        engine = create_asr_engine(config)
        assert isinstance(engine, OnnxParakeetEngine)
    else:
        with pytest.raises(ImportError, match="onnx-asr"):
            create_asr_engine(config)


def test_factory_parakeet_falls_back_to_onnx_without_nemo() -> None:
    """With 'parakeet' engine and no NeMo, factory falls back to ONNX or raises."""
    config = Settings(asr_engine="parakeet")

    if NEMO_AVAILABLE:
        # NeMo is installed — engine is either Parakeet (GPU) or ONNX (CPU).
        engine = create_asr_engine(config)
        assert isinstance(engine, (ParakeetEngine, OnnxParakeetEngine))
    elif ONNX_ASR_AVAILABLE:
        # NeMo absent but ONNX available — should fall back to ONNX.
        engine = create_asr_engine(config)
        assert isinstance(engine, OnnxParakeetEngine)
    else:
        # Neither available — should raise ImportError for onnx-asr.
        with pytest.raises(ImportError, match="onnx-asr"):
            create_asr_engine(config)


def test_factory_engine_name_is_case_insensitive() -> None:
    """Engine names should be matched case-insensitively."""
    # 'WHISPER' should behave the same as 'whisper'.
    config_upper = Settings(asr_engine="WHISPER")
    config_lower = Settings(asr_engine="whisper")

    if FASTER_WHISPER_AVAILABLE:
        e1 = create_asr_engine(config_upper)
        e2 = create_asr_engine(config_lower)
        assert type(e1) is type(e2)
    else:
        with pytest.raises(ImportError):
            create_asr_engine(config_upper)


# ---------------------------------------------------------------------------
# Import guard tests
# ---------------------------------------------------------------------------


def test_parakeet_nemo_available_is_bool() -> None:
    """NEMO_AVAILABLE flag must be a boolean."""
    assert isinstance(NEMO_AVAILABLE, bool)


def test_whisper_faster_whisper_available_is_bool() -> None:
    """FASTER_WHISPER_AVAILABLE flag must be a boolean."""
    assert isinstance(FASTER_WHISPER_AVAILABLE, bool)


def test_onnx_parakeet_available_is_bool() -> None:
    """ONNX_ASR_AVAILABLE flag must be a boolean."""
    assert isinstance(ONNX_ASR_AVAILABLE, bool)


def test_parakeet_engine_raises_import_error_without_nemo() -> None:
    """ParakeetEngine.load_model() must raise ImportError when NeMo is absent."""
    if NEMO_AVAILABLE:
        pytest.skip("NeMo is installed — skip ImportError check.")

    import asyncio

    engine = ParakeetEngine()
    with pytest.raises(ImportError, match="NeMo"):
        asyncio.get_event_loop().run_until_complete(engine.load_model())


def test_whisper_engine_raises_import_error_without_faster_whisper() -> None:
    """WhisperEngine.load_model() must raise ImportError when faster-whisper is absent."""
    if FASTER_WHISPER_AVAILABLE:
        pytest.skip("faster-whisper is installed — skip ImportError check.")

    import asyncio

    engine = WhisperEngine()
    with pytest.raises(ImportError, match="faster-whisper"):
        asyncio.get_event_loop().run_until_complete(engine.load_model())


def test_onnx_engine_raises_import_error_without_onnx_asr() -> None:
    """OnnxParakeetEngine.load_model() must raise ImportError when onnx-asr is absent."""
    if ONNX_ASR_AVAILABLE:
        pytest.skip("onnx-asr is installed — skip ImportError check.")

    import asyncio

    engine = OnnxParakeetEngine()
    with pytest.raises(ImportError, match="onnx-asr"):
        asyncio.get_event_loop().run_until_complete(engine.load_model())


# ---------------------------------------------------------------------------
# Engine property tests (no model loaded)
# ---------------------------------------------------------------------------


def test_parakeet_engine_is_not_loaded_initially() -> None:
    """ParakeetEngine.is_loaded should be False before load_model() is called."""
    engine = ParakeetEngine()
    assert engine.is_loaded is False


def test_whisper_engine_is_not_loaded_initially() -> None:
    """WhisperEngine.is_loaded should be False before load_model() is called."""
    engine = WhisperEngine()
    assert engine.is_loaded is False


def test_onnx_engine_is_not_loaded_initially() -> None:
    """OnnxParakeetEngine.is_loaded should be False before load_model() is called."""
    engine = OnnxParakeetEngine()
    assert engine.is_loaded is False


def test_parakeet_supports_streaming() -> None:
    """ParakeetEngine should report streaming support."""
    assert ParakeetEngine().supports_streaming is True


def test_whisper_supports_streaming() -> None:
    """WhisperEngine should report streaming support."""
    assert WhisperEngine().supports_streaming is True


def test_onnx_parakeet_supports_streaming() -> None:
    """OnnxParakeetEngine should report streaming support."""
    assert OnnxParakeetEngine().supports_streaming is True
