# Task 00: Project Setup & Scaffolding

## Objective
Initialize the complete project structure with all necessary configuration files, dependencies, and development tooling.

## Steps

### 1. Initialize the Electron project
```bash
mkdir -p opennode/electron
cd opennode/electron
npm init -y
```

Install core dependencies:
```bash
npm install electron electron-builder
npm install -D vite @vitejs/plugin-react typescript
npm install react react-dom
npm install -D @types/react @types/react-dom
npm install tailwindcss @tailwindcss/vite
npm install zustand           # state management
npm install ws                # WebSocket client
npm install electron-store    # persistent config
```

### 2. Configure Vite for Electron
Create `vite.config.ts` with:
- Main process build (Node target)
- Renderer process build (Chrome target)
- Preload script build
- Overlay window as separate entry point

Use `vite-plugin-electron` or equivalent for Electron + Vite integration.

### 3. Set up TypeScript
Create `tsconfig.json` with:
- `strict: true`
- Path aliases for `@main/`, `@renderer/`, `@overlay/`, `@shared/`
- Separate configs for main/renderer if needed

### 4. Initialize the Python backend
```bash
mkdir -p opennode/backend
cd opennode/backend
python -m venv .venv
```

Create `pyproject.toml`:
```toml
[project]
name = "opennode-backend"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "websockets>=13",
    "numpy>=1.26",
    "soundfile>=0.12",
    "aiosqlite>=0.20",
    "pydantic>=2.0",
]

[project.optional-dependencies]
gpu = [
    "nemo_toolkit[asr]",
    "torch>=2.1",
]
cpu = [
    "onnx-asr[cpu,hub]",
]
whisper = [
    "faster-whisper>=1.0",
]
diarization = [
    "pyannote.audio>=3.3",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio",
    "ruff",
    "mypy",
]
```

Create `requirements.txt` with pinned versions for reproducibility.

### 5. Create shared types
Create `shared/protocol.ts` with TypeScript interfaces for the WebSocket protocol (see README for message types).

### 6. Create development scripts

`scripts/dev.sh`:
```bash
#!/bin/bash
# Start both backend and frontend in dev mode
# Backend: uvicorn with --reload
# Frontend: vite dev server + electron
```

`scripts/setup.sh`:
```bash
#!/bin/bash
# Full setup: install npm deps, create venv, install pip deps, download models
```

### 7. Create configuration files
- `.gitignore` (node_modules, .venv, __pycache__, dist, models/, *.nemo)
- `.editorconfig`
- `ruff.toml` for Python linting
- `LICENSE` (MIT)

### 8. Create the shared protocol types
Both Python (Pydantic models) and TypeScript (interfaces) for:
- AudioChunkMessage
- ControlMessage
- PartialTranscriptMessage
- FinalTranscriptMessage
- StatusMessage
- SummaryMessage

## Acceptance Criteria
- [ ] `npm install` runs successfully in electron/
- [ ] `pip install -e ".[dev]"` runs successfully in backend/
- [ ] TypeScript compiles without errors
- [ ] Vite dev server starts
- [ ] Python backend starts with `uvicorn opennode.server:app`
- [ ] Shared protocol types exist in both TS and Python
