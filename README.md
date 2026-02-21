# OpenNode - Open Source Meeting Transcription Tool

An open-source, local-first desktop application for real-time meeting transcription, speaker diarization, and summarization. Built with Electron + Python, powered by NVIDIA Parakeet V3.

## Vision

Replace proprietary tools like Notion AI Meeting Notes and Otter.ai with a fully local, privacy-first alternative that:
- Captures system audio (Google Meet, Zoom, Teams, or any audio source)
- Transcribes in real-time using open-source ASR models
- Shows a floating overlay (Picture-in-Picture) with live transcription
- Identifies different speakers (diarization)
- Summarizes meetings after they end
- Works offline — no cloud required

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           Electron App (Frontend)                │
│                                                  │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ System Tray  │  │  Overlay Window (PiP)   │  │
│  │ Controls     │  │  - Live transcript       │  │
│  │              │  │  - Speaker labels        │  │
│  └──────────────┘  │  - Recording indicator   │  │
│                     └─────────────────────────┘  │
│  ┌──────────────────────────────────────────┐    │
│  │ Main Window                              │    │
│  │ - Session history                        │    │
│  │ - Full transcripts                       │    │
│  │ - Meeting summaries                      │    │
│  │ - Settings                               │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Audio Capture Layer                             │
│  ├─ electron-audio-loopback (system audio)       │
│  └─ navigator.mediaDevices (microphone)          │
│                                                  │
│  WebSocket Client ──────────────────┐            │
└─────────────────────────────────────┼────────────┘
                                      │
                              WebSocket (localhost)
                                      │
┌─────────────────────────────────────┼────────────┐
│           Python Backend (FastAPI)   │            │
│                                      ▼            │
│  ┌──────────────────────────────────────────┐    │
│  │ WebSocket Handler                        │    │
│  │ - Receives audio chunks (PCM 16kHz)      │    │
│  │ - Routes to processing pipeline          │    │
│  └──────────────┬───────────────────────────┘    │
│                  │                                │
│  ┌──────────────▼───────────────────────────┐    │
│  │ Audio Processing Pipeline                │    │
│  │                                          │    │
│  │  1. Ring Buffer (accumulate 100-200ms)   │    │
│  │  2. VAD (Silero VAD) → speech/silence    │    │
│  │  3. Chunk Queue (200-500ms segments)     │    │
│  │  4. ASR Worker (Parakeet V3 / fallback)  │    │
│  │  5. Partial/Final transcript emission    │    │
│  └──────────────┬───────────────────────────┘    │
│                  │                                │
│  ┌──────────────▼───────────────────────────┐    │
│  │ Post-Processing (async, non-blocking)    │    │
│  │                                          │    │
│  │  - Speaker Diarization (pyannote)        │    │
│  │  - Meeting Summarization (Ollama/API)    │    │
│  │  - Export (Markdown, JSON, SRT)          │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Data Layer                                      │
│  ├─ SQLite (session metadata)                    │
│  └─ File System (audio files, transcripts)       │
└──────────────────────────────────────────────────┘
```

## Tech Stack

### Frontend (Electron)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Electron 33+ | Desktop app shell |
| UI Framework | React 18 + TypeScript | UI components |
| Bundler | Vite | Fast dev builds |
| Styling | Tailwind CSS | Utility-first CSS |
| Audio Capture | electron-audio-loopback | System audio capture |
| IPC/Comms | WebSocket (ws) | Real-time communication |
| State | Zustand | Lightweight state management |

### Backend (Python)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI + uvicorn | WebSocket server |
| ASR Engine (Primary) | NVIDIA Parakeet TDT 0.6B V3 | Speech-to-text |
| ASR Engine (Fallback) | faster-whisper (large-v3) | Fallback/alternative ASR |
| VAD | Silero VAD | Voice activity detection |
| Diarization | pyannote.audio | Speaker identification |
| Summarization | Ollama (local) or API | Meeting summarization |
| Audio Processing | soundfile, numpy | Audio manipulation |
| Database | SQLite (aiosqlite) | Session storage |

### Model Details

#### NVIDIA Parakeet TDT 0.6B V3
- **HuggingFace**: `nvidia/parakeet-tdt-0.6b-v3`
- **Parameters**: 600M
- **Disk Size**: ~2.5 GB (.nemo), ~640 MB (ONNX INT8)
- **License**: CC-BY-4.0 (commercial use allowed)
- **Languages**: 25 (including Portuguese, Spanish, English, French, German, Italian)
- **Speed**: 6.3x faster than Whisper Large-V3
- **Accuracy**: WER 18.56% (clean), 21.58% (noisy) — better than Whisper
- **Streaming**: Supported via NeMo framework
- **Requirements**:
  - GPU: NVIDIA with Compute Capability >7.0, 4GB+ VRAM recommended
  - CPU: Possible via ONNX runtime (slower, ~6-60x)
  - RAM: 4GB minimum, 8GB recommended

#### faster-whisper Large-V3 (Fallback)
- **Library**: `faster-whisper`
- **Speed**: 4x faster than OpenAI Whisper
- **Languages**: 90+ (broader coverage)
- **GPU**: CTranslate2 with CUDA support
- **Use case**: Fallback for non-European languages

## Hardware Requirements

### Minimum
- CPU: 4 cores, 2.5GHz+
- RAM: 8 GB
- Storage: 5 GB free (models + app)
- GPU: None (CPU-only mode with ONNX, slower)

### Recommended
- CPU: 8 cores, 3.0GHz+
- RAM: 16 GB
- GPU: NVIDIA RTX 3060+ (6GB VRAM)
- Storage: 10 GB free

### Optimal
- CPU: 8+ cores
- RAM: 32 GB
- GPU: NVIDIA RTX 4070+ (12GB VRAM)
- Storage: 20 GB free (for multiple models)

## Platform Support

| Platform | System Audio | Microphone | Notes |
|----------|-------------|------------|-------|
| macOS 12.3+ | Yes (electron-audio-loopback) | Yes | Requires Screen Recording permission |
| Windows 10+ | Yes (WASAPI loopback) | Yes | Best support |
| Linux (PulseAudio) | Yes | Yes | PulseAudio required |

## Project Structure

```
opennode/
├── .claude/
│   └── tasks/                    # Claude Code task files
│       ├── 00-project-setup.md
│       ├── 01-python-backend-core.md
│       ├── 02-asr-engine.md
│       ├── 03-vad-pipeline.md
│       ├── 04-websocket-server.md
│       ├── 05-electron-shell.md
│       ├── 06-audio-capture.md
│       ├── 07-overlay-window.md
│       ├── 08-main-window-ui.md
│       ├── 09-electron-python-integration.md
│       ├── 10-speaker-diarization.md
│       ├── 11-meeting-summarization.md
│       ├── 12-export-and-storage.md
│       ├── 13-settings-and-config.md
│       ├── 14-system-tray.md
│       ├── 15-packaging-and-distribution.md
│       └── 16-testing-and-qa.md
├── electron/                     # Electron frontend
│   ├── src/
│   │   ├── main/                 # Main process
│   │   ├── renderer/             # Renderer (React)
│   │   ├── overlay/              # Overlay window
│   │   └── preload/              # Preload scripts
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── backend/                      # Python backend
│   ├── opennode/
│   │   ├── __init__.py
│   │   ├── server.py             # FastAPI WebSocket server
│   │   ├── asr/                  # ASR engines
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract ASR interface
│   │   │   ├── parakeet.py       # Parakeet V3 engine
│   │   │   └── whisper.py        # faster-whisper fallback
│   │   ├── vad/                  # Voice activity detection
│   │   │   ├── __init__.py
│   │   │   └── silero.py
│   │   ├── pipeline/             # Audio processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── buffer.py         # Ring buffer
│   │   │   └── processor.py      # Main pipeline orchestrator
│   │   ├── diarization/          # Speaker diarization
│   │   │   ├── __init__.py
│   │   │   └── pyannote_engine.py
│   │   ├── summarization/        # Meeting summarization
│   │   │   ├── __init__.py
│   │   │   └── summarizer.py
│   │   ├── storage/              # Data persistence
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   └── config.py             # Configuration
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── tests/
├── shared/                       # Shared types/protocols
│   └── protocol.ts               # WebSocket message types
├── scripts/                      # Setup and utility scripts
│   ├── setup.sh
│   ├── download-models.py
│   └── dev.sh
├── README.md
├── LICENSE                       # MIT
└── .gitignore
```

## WebSocket Protocol

### Client → Server
```json
{
  "type": "audio_chunk",
  "data": "<base64 PCM 16-bit 16kHz mono>",
  "timestamp": 1708531200000,
  "session_id": "uuid"
}

{
  "type": "control",
  "action": "start" | "stop" | "pause" | "resume",
  "session_id": "uuid",
  "config": {
    "language": "auto",
    "model": "parakeet",
    "enable_diarization": true
  }
}
```

### Server → Client
```json
{
  "type": "partial_transcript",
  "text": "Hello w",
  "chunk_id": 1,
  "confidence": 0.87,
  "timestamp_ms": 1500
}

{
  "type": "final_transcript",
  "text": "Hello world",
  "chunk_id": 1,
  "confidence": 0.92,
  "speaker": "Speaker 1",
  "start_ms": 1000,
  "end_ms": 2500
}

{
  "type": "status",
  "state": "ready" | "transcribing" | "error",
  "model_loaded": true,
  "gpu_available": true
}

{
  "type": "summary",
  "session_id": "uuid",
  "summary": "...",
  "action_items": ["..."],
  "key_decisions": ["..."]
}
```

## Key References & Inspirations

- [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes) — Closest existing tool (Rust-based)
- [Buzz](https://github.com/chidiwilliams/buzz) — Desktop transcription with Whisper
- [VoiceStreamAI](https://github.com/alesaccoia/VoiceStreamAI) — WebSocket streaming ASR
- [WhisperLive](https://github.com/collabora/WhisperLive) — Real-time Whisper
- [RealtimeSTT](https://github.com/KoljaB/RealtimeSTT) — Python real-time STT library
- [electron-audio-loopback](https://github.com/alectrocute/electron-audio-loopback) — System audio capture
- [Whispering](https://github.com/braden-w/whispering) — Local-first transcription app
