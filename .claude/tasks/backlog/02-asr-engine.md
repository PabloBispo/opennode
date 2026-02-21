# Task 02: ASR Engine Implementation

## Objective
Implement the speech-to-text engine with Parakeet V3 as primary and faster-whisper as fallback, behind a common interface.

## Steps

### 1. Abstract ASR interface (`backend/opennode/asr/base.py`)
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    start_ms: int
    end_ms: int
    words: list[WordTimestamp]  # word-level timestamps
    is_partial: bool

@dataclass
class WordTimestamp:
    word: str
    start_ms: int
    end_ms: int
    confidence: float

class ASREngine(ABC):
    @abstractmethod
    async def load_model(self) -> None:
        """Load the ASR model into memory."""
        pass

    @abstractmethod
    async def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult:
        """Transcribe an audio chunk."""
        pass

    @abstractmethod
    async def transcribe_stream(self, audio_chunk: np.ndarray) -> TranscriptionResult:
        """Process a streaming audio chunk (with internal state/context)."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Release model from memory."""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        pass
```

### 2. Parakeet V3 engine (`backend/opennode/asr/parakeet.py`)

**Model download:**
```python
# Auto-downloads from HuggingFace on first use
import nemo.collections.asr as nemo_asr
model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3")
```

**Key implementation details:**
- Load model with NeMo toolkit
- Configure for streaming: set `preprocessor.featurizer.dither = 0.0`, `preprocessor.featurizer.pad_to = 16`
- Use `model.transcribe()` with `timestamps=True` for word-level timing
- Handle GPU/CPU fallback gracefully
- Cache model in `~/.opennode/models/`

**Streaming mode:**
- Parakeet supports context-manager based streaming
- Maintain encoder cache between chunks for efficiency
- Configure left/right context frames for attention window

**Audio requirements:**
- PCM 16-bit, 16kHz, mono
- Convert with numpy if needed

### 3. faster-whisper fallback (`backend/opennode/asr/whisper.py`)
```python
from faster_whisper import WhisperModel

class WhisperEngine(ASREngine):
    def __init__(self, model_size="large-v3", device="auto", compute_type="float16"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    async def transcribe(self, audio, sample_rate=16000):
        segments, info = self.model.transcribe(audio, beam_size=5)
        # Convert segments to TranscriptionResult
```

**Key details:**
- Supports 90+ languages (broader than Parakeet)
- 4x faster than OpenAI Whisper
- GPU via CTranslate2 (CUDA)
- 8-bit quantization available for lower VRAM

### 4. ONNX lightweight engine (optional, for CPU-only)
```python
# For machines without GPU
from onnx_asr import Parakeet

class OnnxParakeetEngine(ASREngine):
    def __init__(self):
        self.model = Parakeet()  # Uses ONNX runtime
```

- INT8 quantized: only ~640MB
- Runs on CPU without PyTorch
- Slower but functional

### 5. Engine factory
```python
def create_asr_engine(config: Settings) -> ASREngine:
    if config.asr_engine == "parakeet":
        if torch.cuda.is_available():
            return ParakeetEngine(config)
        else:
            return OnnxParakeetEngine(config)
    elif config.asr_engine == "whisper":
        return WhisperEngine(config)
    raise ValueError(f"Unknown engine: {config.asr_engine}")
```

### 6. Model download script (`scripts/download-models.py`)
```python
"""Download and cache ASR models."""
# Downloads:
# - nvidia/parakeet-tdt-0.6b-v3 (~2.5GB)
# - OR ONNX variant (~640MB)
# - Silero VAD model (~2MB)
# Stores in ~/.opennode/models/
```

## Important Notes
- Parakeet V3 supports Portuguese (pt), which is critical for this project
- The NeMo toolkit is heavy (~5GB with dependencies); consider ONNX for lighter installs
- GPU with 4GB+ VRAM is recommended for Parakeet; 6GB+ for Whisper large-v3
- Model auto-detection: try Parakeet first, fall back to Whisper if language unsupported

## Acceptance Criteria
- [ ] Parakeet engine loads and transcribes a test WAV file
- [ ] Whisper engine loads and transcribes same file
- [ ] ONNX engine works on CPU-only machine
- [ ] Word-level timestamps are returned
- [ ] Language auto-detection works
- [ ] Engine factory selects correct engine based on config/hardware
- [ ] Models are cached in ~/.opennode/models/
