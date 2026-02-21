#!/usr/bin/env bash
# Full setup: install npm deps, create venv, install pip deps

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "⚙️  Setting up OpenNode development environment..."

# ── Node / Electron ────────────────────────────────────────────────────────
echo ""
echo "→ Installing Node dependencies..."
cd "$ROOT/electron"
npm install
echo "  ✓ Node dependencies installed"

# ── Python / Backend ───────────────────────────────────────────────────────
echo ""
echo "→ Setting up Python virtual environment..."
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "  ✓ Created .venv"
else
  echo "  ✓ .venv already exists"
fi

source .venv/bin/activate

echo "→ Installing Python dependencies (base)..."
pip install -e ".[dev]" --quiet
echo "  ✓ Base dependencies installed"

echo ""
echo "Available optional dependency groups:"
echo "  GPU:         pip install -e '.[gpu]'        (NeMo + PyTorch CUDA)"
echo "  CPU/ONNX:    pip install -e '.[cpu]'        (ONNX runtime)"
echo "  Whisper:     pip install -e '.[whisper]'    (faster-whisper fallback)"
echo "  Diarization: pip install -e '.[diarization]' (pyannote.audio)"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start development:"
echo "  ./scripts/dev.sh"
