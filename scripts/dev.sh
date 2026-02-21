#!/usr/bin/env bash
# Start both backend and frontend in development mode

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Starting OpenNode development environment..."

# Start Python backend with auto-reload
echo "→ Starting backend (uvicorn --reload)..."
(
  cd "$ROOT/backend"
  source .venv/bin/activate 2>/dev/null || true
  python -m uvicorn opennode.server:app \
    --host 127.0.0.1 \
    --port 8765 \
    --reload \
    --log-level info &
  echo "  Backend PID: $!"
)

# Wait for backend to be ready
echo "→ Waiting for backend to start..."
for i in $(seq 1 10); do
  if curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo "  Backend is ready!"
    break
  fi
  sleep 1
done

# Start Electron + Vite dev server
echo "→ Starting Electron with Vite HMR..."
(
  cd "$ROOT/electron"
  npm run dev
)
