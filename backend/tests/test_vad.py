"""Tests for the VAD pipeline — ring buffer, speech accumulator, and data classes.

All tests here run WITHOUT needing torch or silero-vad installed.
"""

from __future__ import annotations

import time

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# AudioRingBuffer tests
# ---------------------------------------------------------------------------


def test_ring_buffer_write_read() -> None:
    """Basic write then read returns the expected samples."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    audio = np.ones(1600, dtype=np.float32)
    buf.write(audio)
    assert buf.available() == 1600
    out = buf.read(800)
    assert len(out) == 800
    assert buf.available() == 800


def test_ring_buffer_write_values_preserved() -> None:
    """Values written to the buffer are returned correctly."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    audio = np.arange(100, dtype=np.float32)
    buf.write(audio)
    out = buf.read(100)
    np.testing.assert_array_equal(out, audio)


def test_ring_buffer_overflow() -> None:
    """Writing more than max_samples keeps only the latest data."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    # Write 20000 samples into a 16000-sample buffer
    audio = np.arange(20000, dtype=np.float32)
    buf.write(audio)
    # Available should be capped at max_samples
    assert buf.available() == 16000
    # The data returned should be the latest 16000 samples
    out = buf.read_all()
    np.testing.assert_array_equal(out, audio[-16000:])


def test_ring_buffer_read_all() -> None:
    """read_all returns all data and leaves the buffer empty."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    audio = np.ones(500, dtype=np.float32)
    buf.write(audio)
    out = buf.read_all()
    assert len(out) == 500
    assert buf.available() == 0


def test_ring_buffer_read_all_empty() -> None:
    """read_all on an empty buffer returns an empty array."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    out = buf.read_all()
    assert len(out) == 0


def test_ring_buffer_clear() -> None:
    """clear() resets the buffer to empty."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    buf.write(np.ones(1000, dtype=np.float32))
    buf.clear()
    assert buf.available() == 0
    out = buf.read_all()
    assert len(out) == 0


def test_ring_buffer_duration_ms() -> None:
    """duration_ms correctly converts sample count to milliseconds."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    buf.write(np.zeros(8000, dtype=np.float32))  # 500 ms at 16kHz
    assert buf.duration_ms == pytest.approx(500.0)


def test_ring_buffer_is_full() -> None:
    """is_full returns True when the buffer capacity is reached."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    assert not buf.is_full
    buf.write(np.zeros(16000, dtype=np.float32))
    assert buf.is_full


def test_ring_buffer_partial_read_then_write() -> None:
    """Partial reads and subsequent writes interleave correctly."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    buf.write(np.ones(1000, dtype=np.float32) * 1.0)
    buf.read(500)  # consume half
    buf.write(np.ones(500, dtype=np.float32) * 2.0)
    assert buf.available() == 1000
    out = buf.read_all()
    assert len(out) == 1000
    np.testing.assert_array_equal(out[:500], np.ones(500) * 1.0)
    np.testing.assert_array_equal(out[500:], np.ones(500) * 2.0)


def test_ring_buffer_wrap_around() -> None:
    """Data that wraps around the internal buffer boundary is read correctly."""
    from opennode.pipeline.buffer import AudioRingBuffer

    # Use a tiny buffer (10 samples) to force wrap-around easily
    buf = AudioRingBuffer(max_duration_seconds=10 / 16000, sample_rate=16000)
    # max_samples = 10
    buf.write(np.arange(8, dtype=np.float32))  # write 8, pos=8
    buf.read(6)  # consume 6, available=2, read_start=6
    # Write 6 more: wraps from pos=8 -> end -> start
    new_data = np.arange(10, 16, dtype=np.float32)
    buf.write(new_data)
    out = buf.read_all()
    assert len(out) == 8
    np.testing.assert_array_equal(out[:2], np.arange(6, 8, dtype=np.float32))
    np.testing.assert_array_equal(out[2:], new_data)


def test_ring_buffer_read_more_than_available() -> None:
    """Reading more samples than available returns only what is available."""
    from opennode.pipeline.buffer import AudioRingBuffer

    buf = AudioRingBuffer(max_duration_seconds=1.0, sample_rate=16000)
    buf.write(np.ones(100, dtype=np.float32))
    out = buf.read(500)
    assert len(out) == 100


# ---------------------------------------------------------------------------
# SpeechAccumulator tests
# ---------------------------------------------------------------------------


def _make_chunk(n: int = 512, value: float = 0.1) -> "VADResult":  # type: ignore[name-defined]  # noqa: F821
    """Helper: build a VADResult without importing torch."""
    from opennode.vad.silero import VADResult

    return VADResult(
        is_speech=True,
        probability=0.9,
        audio=np.full(n, value, dtype=np.float32),
    )


def _make_silence_chunk(n: int = 512) -> "VADResult":  # type: ignore[name-defined]  # noqa: F821
    from opennode.vad.silero import VADResult

    return VADResult(
        is_speech=False,
        probability=0.1,
        audio=np.zeros(n, dtype=np.float32),
    )


def test_speech_accumulator_emits_on_silence() -> None:
    """Accumulator emits an utterance after silence_timeout_ms of silence."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(
        min_speech_ms=100,
        silence_timeout_ms=200,
        sample_rate=16000,
    )
    chunk = np.ones(512, dtype=np.float32) * 0.1

    # Add 10 speech chunks (~320ms total)
    for _ in range(10):
        from opennode.vad.silero import VADResult

        result = acc.add_chunk(VADResult(is_speech=True, probability=0.9, audio=chunk))
        assert result is None  # still accumulating

    # Wait for the silence timeout then add a silence chunk
    time.sleep(0.25)
    from opennode.vad.silero import VADResult

    result = acc.add_chunk(VADResult(is_speech=False, probability=0.1, audio=chunk))
    assert result is not None  # utterance complete


def test_speech_accumulator_no_emit_without_enough_speech() -> None:
    """Accumulator discards very short speech followed by silence."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(
        min_speech_ms=500,
        silence_timeout_ms=100,
        sample_rate=16000,
    )
    # Add only 1 speech chunk (~32ms — well below min_speech_ms=500ms)
    result = acc.add_chunk(_make_chunk())
    assert result is None

    # Wait for silence timeout, then add silence
    time.sleep(0.15)
    result = acc.add_chunk(_make_silence_chunk())
    assert result is None  # discarded — too short
    assert not acc.is_in_speech


def test_speech_accumulator_emits_on_max_speech() -> None:
    """Accumulator force-emits when max_speech_ms is reached."""
    from opennode.vad.accumulator import SpeechAccumulator

    # Very small max_speech_ms so we hit it quickly
    acc = SpeechAccumulator(
        min_speech_ms=0,
        max_speech_ms=100,
        silence_timeout_ms=5000,
        sample_rate=16000,
    )
    # 512 samples = ~32ms; 4 chunks = ~128ms > 100ms
    emitted = None
    for _ in range(10):
        emitted = acc.add_chunk(_make_chunk())
        if emitted is not None:
            break

    assert emitted is not None


def test_speech_accumulator_is_in_speech() -> None:
    """is_in_speech reflects whether we are inside a speech segment."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(sample_rate=16000)
    assert not acc.is_in_speech
    acc.add_chunk(_make_chunk())
    assert acc.is_in_speech


def test_speech_accumulator_accumulated_ms() -> None:
    """accumulated_ms returns total duration accumulated so far."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(sample_rate=16000)
    chunk_ms = (512 / 16000) * 1000  # ~32ms
    acc.add_chunk(_make_chunk(512))
    assert acc.accumulated_ms == pytest.approx(chunk_ms, rel=0.01)


def test_speech_accumulator_reset() -> None:
    """reset() clears all state."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(sample_rate=16000)
    acc.add_chunk(_make_chunk())
    assert acc.is_in_speech
    acc.reset()
    assert not acc.is_in_speech
    assert acc.accumulated_ms == 0.0


def test_speech_accumulator_get_partial() -> None:
    """get_partial returns audio after partial_interval_ms has elapsed."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(
        partial_interval_ms=50,
        sample_rate=16000,
    )
    acc.add_chunk(_make_chunk())
    # Before the interval — should return None
    result = acc.get_partial()
    assert result is None

    # After the interval — should return partial audio
    time.sleep(0.06)
    result = acc.get_partial()
    assert result is not None
    assert len(result) > 0


def test_speech_accumulator_get_partial_not_in_speech() -> None:
    """get_partial returns None when not in a speech segment."""
    from opennode.vad.accumulator import SpeechAccumulator

    acc = SpeechAccumulator(sample_rate=16000)
    assert acc.get_partial() is None


# ---------------------------------------------------------------------------
# VADResult and SpeechSegment dataclass tests
# ---------------------------------------------------------------------------


def test_vad_result_dataclass() -> None:
    """VADResult stores fields correctly."""
    from opennode.vad.silero import VADResult

    r = VADResult(is_speech=True, probability=0.9, audio=np.zeros(512))
    assert r.is_speech is True
    assert r.probability == pytest.approx(0.9)
    assert len(r.audio) == 512


def test_vad_result_not_speech() -> None:
    """VADResult with is_speech=False."""
    from opennode.vad.silero import VADResult

    r = VADResult(is_speech=False, probability=0.1, audio=np.zeros(512))
    assert r.is_speech is False


def test_speech_segment_duration_ms() -> None:
    """SpeechSegment.duration_ms converts sample indices to milliseconds correctly."""
    from opennode.vad.silero import SpeechSegment

    seg = SpeechSegment(start=0, end=16000)
    assert seg.duration_ms == pytest.approx(1000.0)


def test_speech_segment_duration_ms_partial() -> None:
    """SpeechSegment.duration_ms for a 500ms segment."""
    from opennode.vad.silero import SpeechSegment

    seg = SpeechSegment(start=0, end=8000)
    assert seg.duration_ms == pytest.approx(500.0)


def test_speech_segment_non_zero_start() -> None:
    """SpeechSegment.duration_ms uses difference of start and end."""
    from opennode.vad.silero import SpeechSegment

    seg = SpeechSegment(start=8000, end=16000)
    assert seg.duration_ms == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# Import guard test
# ---------------------------------------------------------------------------


def test_silero_vad_requires_torch() -> None:
    """SileroVAD should raise ImportError if silero-vad/torch are not installed."""
    from opennode.vad import silero

    if not silero.SILERO_AVAILABLE:
        with pytest.raises(ImportError):
            silero.SileroVAD()
    else:
        # If torch IS available, at least verify the class is instantiable
        # (we don't load the model in unit tests — just verify no crash on import)
        pytest.skip("silero-vad is installed; skipping ImportError guard test")


def test_silero_available_flag_is_bool() -> None:
    """SILERO_AVAILABLE must always be a boolean regardless of install state."""
    from opennode.vad import silero

    assert isinstance(silero.SILERO_AVAILABLE, bool)
