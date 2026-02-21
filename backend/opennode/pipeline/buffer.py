"""Thread-safe circular (ring) buffer for audio accumulation."""

from __future__ import annotations

import threading

import numpy as np


class AudioRingBuffer:
    """Thread-safe circular buffer for audio accumulation.

    Stores float32 audio samples in a fixed-size ring buffer.
    When the buffer is full, new writes overwrite the oldest data.

    Example:
        buf = AudioRingBuffer(max_duration_seconds=30.0, sample_rate=16000)
        buf.write(audio_chunk)
        audio = buf.read_all()
    """

    def __init__(
        self,
        max_duration_seconds: float = 30.0,
        sample_rate: int = 16000,
    ) -> None:
        """Initialize the ring buffer.

        Args:
            max_duration_seconds: Maximum audio duration to hold in seconds.
            sample_rate: Audio sample rate in Hz. Used to convert duration to samples.
        """
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration_seconds * sample_rate)
        self._buffer = np.zeros(self.max_samples, dtype=np.float32)
        self._write_pos = 0
        self._available = 0
        self._lock = threading.Lock()

    def write(self, audio: np.ndarray) -> int:
        """Write audio samples to the buffer.

        When the buffer overflows, the oldest data is overwritten.

        Args:
            audio: Float32 numpy array of audio samples to write.

        Returns:
            Number of samples actually written (may be less if truncated to max_samples).
        """
        with self._lock:
            n = len(audio)
            # If the incoming data is larger than the buffer, keep only the latest portion
            if n > self.max_samples:
                audio = audio[-self.max_samples :]
                n = self.max_samples

            # How many samples fit before wrapping around
            space_to_end = self.max_samples - self._write_pos

            if n <= space_to_end:
                self._buffer[self._write_pos : self._write_pos + n] = audio
            else:
                # Split across the wrap boundary
                first_part = space_to_end
                second_part = n - first_part
                self._buffer[self._write_pos :] = audio[:first_part]
                self._buffer[:second_part] = audio[first_part:]

            self._write_pos = (self._write_pos + n) % self.max_samples

            # Track available samples (capped at max_samples on overflow)
            self._available = min(self._available + n, self.max_samples)

            return n

    def read(self, num_samples: int) -> np.ndarray:
        """Read up to num_samples from the buffer (oldest-first, FIFO).

        The read data is consumed and is no longer available.

        Args:
            num_samples: Maximum number of samples to read.

        Returns:
            Float32 numpy array of up to num_samples samples.
        """
        with self._lock:
            n = min(num_samples, self._available)
            if n == 0:
                return np.array([], dtype=np.float32)

            # Calculate the read start position
            read_start = (self._write_pos - self._available) % self.max_samples
            read_end = (read_start + n) % self.max_samples

            if read_end > read_start:
                # Contiguous read
                result = self._buffer[read_start:read_end].copy()
            else:
                # Wrap-around read
                first_part = self._buffer[read_start:].copy()
                second_part = self._buffer[:read_end].copy()
                result = np.concatenate([first_part, second_part])

            self._available -= n
            return result

    def read_all(self) -> np.ndarray:
        """Read all available samples and reset the buffer state.

        Returns:
            Float32 numpy array of all available samples.
        """
        with self._lock:
            if self._available == 0:
                return np.array([], dtype=np.float32)

            read_start = (self._write_pos - self._available) % self.max_samples
            n = self._available

            read_end = (read_start + n) % self.max_samples

            if read_end > read_start:
                result = self._buffer[read_start:read_end].copy()
            else:
                first_part = self._buffer[read_start:].copy()
                second_part = self._buffer[:read_end].copy()
                result = np.concatenate([first_part, second_part])

            self._available = 0
            return result

    def available(self) -> int:
        """Return the number of unread samples currently in the buffer."""
        with self._lock:
            return self._available

    def clear(self) -> None:
        """Reset the buffer, discarding all data."""
        with self._lock:
            self._write_pos = 0
            self._available = 0
            self._buffer[:] = 0.0

    @property
    def is_full(self) -> bool:
        """True if the buffer has no more free space."""
        with self._lock:
            return self._available >= self.max_samples

    @property
    def duration_ms(self) -> float:
        """Duration of available audio in milliseconds (assuming 16kHz sample rate)."""
        with self._lock:
            return (self._available / self.sample_rate) * 1000.0
