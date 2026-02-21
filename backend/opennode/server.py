"""OpenNode FastAPI server."""

from __future__ import annotations

import base64
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger

from .config import settings
from .storage import DataManager, export_json, export_markdown, export_srt, export_txt
from .utils import check_gpu
from .asr.factory import create_asr_engine
from .pipeline.connection_manager import ConnectionManager
from .pipeline.session import TranscriptionSession
from .protocol import AudioChunkMessage, ControlMessage

# Module-level reference so endpoints can access it without going through request.app.state
data_manager: Optional[DataManager] = None

# Module-level singletons (initialized in lifespan)
_connection_manager: ConnectionManager = ConnectionManager()
_asr_engine = None  # initialized in lifespan when models are available


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    global data_manager, _asr_engine

    logger.info(f"OpenNode backend starting on {settings.host}:{settings.port}")
    logger.info(f"ASR engine: {settings.asr_engine}")
    logger.info(f"Diarization: {settings.enable_diarization}")

    # Initialize storage directories and database
    data_manager = DataManager(settings.data_dir)
    await data_manager.initialize()
    app.state.db = data_manager
    logger.info(f"Data directory: {data_manager.data_dir}")

    # Log GPU info at startup
    gpu_info = check_gpu()
    if gpu_info["available"]:
        logger.info(f"GPU detected: {gpu_info['name']} ({gpu_info['vram_mb']} MB VRAM)")
    else:
        logger.info("No CUDA GPU detected — running on CPU")

    # Initialize ASR engine (optional — transcription degraded if unavailable)
    try:
        _asr_engine = create_asr_engine(settings)
        await _asr_engine.load_model()
        logger.info(f"ASR engine loaded: {settings.asr_engine}")
    except Exception as e:
        logger.warning(f"ASR engine not loaded: {e} — transcription will be unavailable")
        _asr_engine = None

    yield

    logger.info("OpenNode backend shutting down")
    if data_manager is not None:
        await data_manager.close()


app = FastAPI(
    title="OpenNode Backend",
    version="0.1.0",
    description="Real-time meeting transcription backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ───────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:  # type: ignore[type-arg]
    """Health check with GPU info."""
    from .utils import check_gpu

    gpu_info = check_gpu()
    return {
        "status": "ok",
        "version": "0.1.0",
        "gpu_available": gpu_info["available"],
        "gpu_info": gpu_info,
    }


# ─── Status API ───────────────────────────────────────────────────────────────


@app.get("/api/status")
async def get_status() -> dict:  # type: ignore[type-arg]
    """Return server status including active sessions, ASR engine, and GPU info."""
    from .utils import check_gpu
    gpu = check_gpu()
    return {
        "active_sessions": _connection_manager.active_count,
        "asr_engine": settings.asr_engine,
        "model_loaded": bool(_asr_engine and _asr_engine.is_loaded),
        "gpu_available": gpu["available"],
        "gpu_info": gpu,
    }


# ─── WebSocket ────────────────────────────────────────────────────────────────


@app.websocket("/ws/transcribe")
async def transcribe_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time transcription."""
    await websocket.accept()
    session = await _connection_manager.connect(websocket, _asr_engine)

    # Send initial status
    await session._send_status("ready")

    try:
        async for raw in websocket.iter_text():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received on WebSocket")
                continue

            msg_type = data.get("type")

            if msg_type == "audio_chunk":
                try:
                    audio_bytes = base64.b64decode(data["data"])
                    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    timestamp = data.get("timestamp", 0)
                    await session.process_audio(audio, timestamp)
                except Exception as e:
                    logger.error(f"Audio processing error: {e}")

            elif msg_type == "control":
                action = data.get("action", "")
                config = data.get("config")
                if action == "start":
                    await session.start(config)
                elif action == "stop":
                    await session.stop()
                elif action == "pause":
                    await session.pause()
                elif action == "resume":
                    await session.resume()
                else:
                    logger.warning(f"Unknown control action: {action}")

            else:
                logger.warning(f"Unknown message type: {msg_type}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session.session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await _connection_manager.disconnect(session.session_id)


# ─── Sessions API ─────────────────────────────────────────────────────────────


def _get_db(request: Request) -> DataManager:
    """Extract the DataManager from app state, raising 503 if not ready."""
    dm: Optional[DataManager] = getattr(request.app.state, "db", None)
    if dm is None:
        raise HTTPException(status_code=503, detail="Storage not initialised")
    return dm


@app.get("/api/sessions")
async def list_sessions(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> JSONResponse:
    """Return a paginated list of sessions."""
    dm = _get_db(request)
    sessions = await dm.db.list_sessions(limit=limit, offset=offset, status=status)

    def _serialise_session(s):  # type: ignore[no-untyped-def]
        return {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "duration_ms": s.duration_ms,
            "language": s.language,
            "model_used": s.model_used,
            "audio_source": s.audio_source,
            "status": s.status,
        }

    return JSONResponse(
        content={
            "sessions": [_serialise_session(s) for s in sessions],
            "limit": limit,
            "offset": offset,
        }
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> JSONResponse:
    """Return a single session with its transcripts, summary, and speakers."""
    dm = _get_db(request)
    full_session = await dm.db.get_full_session(session_id)
    if full_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return JSONResponse(content=export_json(full_session))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, request: Request) -> JSONResponse:
    """Delete a session and all its associated data."""
    dm = _get_db(request)
    session = await dm.db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await dm.db.delete_session(session_id)
    return JSONResponse(content={"deleted": session_id})


@app.get("/api/sessions/{session_id}/export/{format}", response_model=None)
async def export_session(
    session_id: str,
    format: str,
    request: Request,
) -> PlainTextResponse | JSONResponse:
    """Export a session in the requested format.

    Supported formats: ``markdown``, ``srt``, ``json``, ``txt``.
    """
    dm = _get_db(request)
    full_session = await dm.db.get_full_session(session_id)
    if full_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    fmt = format.lower()

    if fmt == "markdown":
        content = export_markdown(full_session)
        return PlainTextResponse(content=content, media_type="text/markdown")

    if fmt == "srt":
        content = export_srt(full_session)
        return PlainTextResponse(content=content, media_type="text/plain")

    if fmt == "json":
        return JSONResponse(content=export_json(full_session))

    if fmt == "txt":
        content = export_txt(full_session)
        return PlainTextResponse(content=content, media_type="text/plain")

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported format '{format}'. Use one of: markdown, srt, json, txt",
    )
