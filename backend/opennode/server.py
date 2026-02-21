"""OpenNode FastAPI server."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger

from .config import settings
from .storage import DataManager, export_json, export_markdown, export_srt, export_txt
from .utils import check_gpu

# Module-level reference so endpoints can access it without going through request.app.state
data_manager: Optional[DataManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    global data_manager

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


# ─── WebSocket ────────────────────────────────────────────────────────────────


@app.websocket("/ws/transcribe")
async def transcribe(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time transcription.

    Implemented in Task 04.
    """
    await websocket.accept()
    from loguru import logger
    from .protocol import StatusMessage

    status = StatusMessage(
        state="ready",
        model_loaded=False,
        gpu_available=False,
    )
    await websocket.send_text(status.model_dump_json())
    await websocket.close()


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
