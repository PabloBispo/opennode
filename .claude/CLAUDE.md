# CLAUDE.md — OpenNode Project Instructions

## What is this project?

OpenNode is an open-source desktop application for real-time meeting transcription, speaker diarization, and summarization. It uses Electron (React + TypeScript) for the frontend and Python (FastAPI) for the backend, powered by NVIDIA Parakeet V3 for speech-to-text.

Read `README.md` at the project root for the full architecture, tech stack, and project structure.

## Your Job

This project is built entirely by Claude Code agents. All implementation tasks are defined as Markdown files inside `.claude/tasks/`.

**When you start a session, your first action should be:**

1. Read this file (you're doing it now)
2. Read `.claude/tasks/README.md` for the task system rules
3. Check which tasks are available in `.claude/tasks/backlog/`
4. Check what's already done in `.claude/tasks/done/`
5. Check what's in progress in `.claude/tasks/in-progress/` (another agent may be working)
6. Pick the lowest-numbered task from `backlog/` whose dependencies are satisfied
7. **Move the task file to `in-progress/`** before you start coding
8. Execute the task fully, verifying all acceptance criteria
9. **Move the task file to `done/`** when complete
10. Repeat from step 3

## Task Directories

```
.claude/tasks/
├── backlog/        ← Tasks waiting to be picked up. Grab from here.
├── in-progress/    ← Tasks currently being worked on. Move here when you start.
└── done/           ← Completed tasks. Move here when you finish.
```

Moving files between directories is the coordination mechanism. It prevents multiple agents from working on the same task. **Always move before you start, always move when you finish.**

## Dependency Rules

Not all tasks can run in any order. Check the dependency map in `.claude/tasks/README.md`. The key rule: **only pick a task if all its dependencies are in `done/`.**

Quick reference for parallelism:
- `00` must be done first (project scaffolding)
- `01` and `05` can run in parallel after `00`
- `02`, `03`, `12` can run in parallel after `01`
- `04` needs both `02` and `03`
- And so on — see the full map in the tasks README

## Code Conventions

### Python (backend/)
- Python 3.10+
- Use `async/await` everywhere (FastAPI is async-first)
- Type hints on all functions
- Pydantic models for data validation
- Lint with `ruff`
- Tests with `pytest` + `pytest-asyncio`

### TypeScript (electron/)
- Strict TypeScript (`strict: true`)
- React functional components with hooks
- Zustand for state management
- Tailwind CSS for styling
- Vite for bundling

### General
- Commit after each completed task: `feat(opennode): complete task NN - <title>`
- Keep files small and focused — one concern per file
- Write docstrings/comments for non-obvious logic
- All new code should have corresponding types/interfaces

## Project Structure Reference

```
opennode/
├── .claude/
│   ├── CLAUDE.md              ← This file
│   └── tasks/
│       ├── README.md          ← Task system docs
│       ├── backlog/           ← Available tasks
│       ├── in-progress/       ← Tasks being worked on
│       └── done/              ← Completed tasks
├── electron/                  ← Electron + React frontend
│   ├── src/
│   │   ├── main/              ← Electron main process
│   │   ├── renderer/          ← React UI
│   │   ├── overlay/           ← PiP overlay window
│   │   └── preload/           ← Preload scripts
│   └── package.json
├── backend/                   ← Python FastAPI backend
│   ├── opennode/
│   │   ├── server.py
│   │   ├── asr/               ← ASR engines (Parakeet, Whisper)
│   │   ├── vad/               ← Voice activity detection
│   │   ├── pipeline/          ← Audio processing pipeline
│   │   ├── diarization/       ← Speaker identification
│   │   ├── summarization/     ← Meeting summarization
│   │   ├── storage/           ← Database + file storage
│   │   └── config.py
│   └── pyproject.toml
├── shared/                    ← Shared protocol types
├── scripts/                   ← Setup and dev scripts
└── README.md                  ← Architecture docs
```

## Important Technical Context

- **Primary ASR model**: `nvidia/parakeet-tdt-0.6b-v3` via NeMo or ONNX
- **Fallback ASR**: `faster-whisper` with `large-v3`
- **VAD**: Silero VAD (30ms chunks, threshold 0.5)
- **Diarization**: pyannote.audio 3.1
- **Communication**: WebSocket on `ws://127.0.0.1:8765/ws/transcribe`
- **Audio format**: PCM 16-bit, 16kHz, mono
- **Data stored in**: `~/.opennode/` (SQLite + audio files + models)

## When in Doubt

- Read the task file thoroughly — it has code snippets and implementation details
- Read `README.md` for architecture decisions and the WebSocket protocol
- Check existing code in `done/` tasks for patterns already established
- Prefer simplicity: get it working first, optimize later
