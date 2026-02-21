# Task 03: Voice Activity Detection Pipeline

## Objective
Implement Voice Activity Detection (VAD) using Silero VAD to detect speech segments and optimize ASR processing.

## Steps

### 1. Silero VAD wrapper (`backend/opennode/vad/silero.py`)

**Installation:**
```bash
pip install silero-vad
# OR torch-based:
# pip install torch torchaudio
```

**Implementation:**
```python
import torch
from silero_vad import load_silero_vad, get_speech_timestamps

class SileroVAD:
    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.model = load_silero_vad()
        self._reset_state()

    def _reset_state(self):
        """Reset internal model state for new session."""
        self.model.reset_states()

    def process_chunk(self, audio_chunk: np.ndarray) -> VADResult:
        """Process a single audio chunk and return speech probability."""
        tensor = torch.from_numpy(audio_chunk).float()
        prob = self.model(tensor, self.sample_rate).item()
        return VADResult(
            is_speech=prob >= self.threshold,
            probability=prob,
            audio=audio_chunk
        )

    def get_speech_segments(self, audio: np.ndarray) -> list[SpeechSegment]:
        """Get speech timestamps from full audio."""
        tensor = torch.from_numpy(audio).float()
        timestamps = get_speech_timestamps(
            tensor, self.model,
            threshold=self.threshold,
            sampling_rate=self.sample_rate,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100,
            speech_pad_ms=30
        )
        return [SpeechSegment(start=t['start'], end=t['end']) for t in timestamps]
```

### 2. Data classes
```python
@dataclass
class VADResult:
    is_speech: bool
    probability: float
    audio: np.ndarray

@dataclass
class SpeechSegment:
    start: int  # sample index
    end: int    # sample index

    @property
    def duration_ms(self) -> float:
        return (self.end - self.start) / 16  # at 16kHz
```

### 3. Ring buffer (`backend/opennode/pipeline/buffer.py`)
```python
class AudioRingBuffer:
    """Efficient circular buffer for audio accumulation."""

    def __init__(self, max_duration_seconds: float = 30.0, sample_rate: int = 16000):
        self.max_samples = int(max_duration_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.write_pos = 0
        self.read_pos = 0

    def write(self, audio: np.ndarray) -> None:
        """Write audio data to buffer."""
        pass

    def read(self, num_samples: int) -> np.ndarray:
        """Read audio data from buffer."""
        pass

    def available(self) -> int:
        """Number of samples available to read."""
        pass
```

### 4. Speech accumulator
Manages the logic of accumulating speech chunks and deciding when to send to ASR:
```python
class SpeechAccumulator:
    """Accumulates speech chunks between silence periods."""

    def __init__(self,
                 min_speech_ms: int = 250,
                 max_speech_ms: int = 30000,
                 silence_timeout_ms: int = 500):
        pass

    def add_chunk(self, vad_result: VADResult) -> Optional[np.ndarray]:
        """
        Add a VAD-processed chunk.
        Returns accumulated speech audio when silence is detected
        (end of utterance) or max duration reached.
        Returns None if still accumulating.
        """
        pass
```

### 5. VAD performance tuning
- **Chunk size for VAD**: 30ms (480 samples at 16kHz) — Silero's optimal size
- **Threshold**: 0.5 default, configurable
- **Min speech duration**: 250ms (avoid false triggers)
- **Min silence for split**: 500ms (natural pause between sentences)
- **Speech padding**: 30ms before/after (avoid cutting words)

## Key Behaviors
- VAD runs on every incoming audio chunk (~30ms)
- When speech is detected, audio accumulates in the speech buffer
- When silence is detected after speech, the accumulated audio is sent to ASR
- For "live" partial transcripts, send to ASR every 500ms even during continuous speech
- Reset VAD state at session start/stop

## Acceptance Criteria
- [ ] Silero VAD loads and processes audio chunks
- [ ] Ring buffer correctly handles circular writes/reads
- [ ] Speech accumulator correctly detects start/end of utterances
- [ ] Silence periods are not sent to ASR (saves compute)
- [ ] Sub-30ms processing time per VAD chunk
- [ ] Memory usage stays stable over long sessions
