# Task 01: Python Backend Core

## Objective
Create the FastAPI application skeleton with health checks, configuration management, and the basic server structure.

## Steps

### 1. Create the FastAPI application (`backend/opennode/server.py`)
```python
from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI(title="OpenNode Backend", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "gpu_available": check_gpu()}

@app.websocket("/ws/transcribe")
async def transcribe(websocket: WebSocket):
    # Will be implemented in Task 04
    pass
```

### 2. Configuration system (`backend/opennode/config.py`)
Use Pydantic Settings for configuration:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    host: str = "127.0.0.1"
    port: int = 8765

    # ASR
    asr_engine: str = "parakeet"  # "parakeet" | "whisper" | "onnx"
    model_path: str = ""  # auto-download if empty
    language: str = "auto"

    # Audio
    sample_rate: int = 16000
    chunk_duration_ms: int = 200
    vad_threshold: float = 0.5

    # Diarization
    enable_diarization: bool = True
    max_speakers: int = 10

    # Summarization
    enable_summarization: bool = True
    summarization_provider: str = "ollama"  # "ollama" | "api"
    ollama_model: str = "llama3.2"

    # Storage
    data_dir: str = "~/.opennode"

    class Config:
        env_prefix = "OPENNODE_"
```

### 3. GPU detection utility
```python
def check_gpu() -> dict:
    """Check if CUDA GPU is available and return info."""
    # Check torch.cuda.is_available()
    # Return device name, VRAM, compute capability
```

### 4. Logging setup
- Structured logging with `loguru` or standard `logging`
- Log to file and console
- Configurable log level

### 5. Application lifecycle
- Startup event: load models, initialize pipeline
- Shutdown event: cleanup resources, close connections

### 6. Entry point
Create `backend/opennode/__main__.py`:
```python
if __name__ == "__main__":
    uvicorn.run("opennode.server:app", host=settings.host, port=settings.port)
```

## Acceptance Criteria
- [ ] `python -m opennode` starts the server
- [ ] `/health` endpoint returns status with GPU info
- [ ] Configuration loads from environment variables
- [ ] Server starts on configurable host:port
- [ ] Graceful shutdown works
