# Task 16: Testing and Quality Assurance

## Objective
Implement testing infrastructure for both the Python backend and Electron frontend.

## Steps

### 1. Python backend tests (`backend/tests/`)

**Unit tests:**
```
tests/
├── test_asr/
│   ├── test_parakeet.py
│   ├── test_whisper.py
│   └── test_engine_factory.py
├── test_vad/
│   └── test_silero.py
├── test_pipeline/
│   ├── test_buffer.py
│   ├── test_processor.py
│   └── test_session.py
├── test_storage/
│   └── test_database.py
├── test_summarization/
│   └── test_summarizer.py
├── test_export/
│   ├── test_markdown.py
│   ├── test_srt.py
│   └── test_json.py
└── conftest.py           # fixtures (test audio files, mock models)
```

**Test fixtures:**
- Sample WAV files (16kHz, mono, various durations)
- Pre-recorded meeting audio for integration tests
- Mock ASR engine that returns canned responses (for fast tests)

**Key tests:**
- Ring buffer correctness (boundary conditions)
- VAD correctly detects speech/silence
- WebSocket message parsing and validation
- Database CRUD operations
- Export format correctness
- Pipeline end-to-end (audio → transcript)

### 2. Electron frontend tests

```
electron/src/__tests__/
├── components/
│   ├── TranscriptLine.test.tsx
│   ├── OverlayApp.test.tsx
│   └── SessionView.test.tsx
├── services/
│   ├── ws-client.test.ts
│   └── audio-capture.test.ts
└── store/
    └── app-store.test.ts
```

Use Vitest (native to Vite) + React Testing Library.

### 3. Integration tests

- Full pipeline: capture audio → WebSocket → VAD → ASR → transcript displayed
- Session lifecycle: start → transcribe → stop → save → load
- Export: record → export markdown → verify output

### 4. Performance benchmarks

```python
# benchmarks/
# - ASR latency per chunk size
# - VAD processing time
# - Memory usage over 1-hour session
# - WebSocket throughput
```

### 5. Test commands
```json
{
  "scripts": {
    "test": "vitest",
    "test:e2e": "playwright test"
  }
}
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 6. Linting and formatting
- Python: `ruff` for linting + formatting
- TypeScript: `eslint` + `prettier`
- Pre-commit hooks (optional)

## Acceptance Criteria
- [ ] Python tests pass with `pytest`
- [ ] Frontend tests pass with `vitest`
- [ ] Code linting passes (ruff, eslint)
- [ ] Test audio fixtures are available
- [ ] Mock ASR engine works for fast testing
- [ ] CI can run tests without GPU (mock mode)
- [ ] Performance benchmarks exist
