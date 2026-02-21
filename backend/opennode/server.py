"""OpenNode FastAPI server."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    logger.info(f"OpenNode backend starting on {settings.host}:{settings.port}")
    logger.info(f"ASR engine: {settings.asr_engine}")
    logger.info(f"Diarization: {settings.enable_diarization}")
    yield
    logger.info("OpenNode backend shutting down")


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


@app.get("/health")
async def health() -> dict:
    """Health check with GPU info."""
    from .utils import check_gpu

    gpu_info = check_gpu()
    return {
        "status": "ok",
        "version": "0.1.0",
        "gpu_available": gpu_info["available"],
        "gpu_info": gpu_info,
    }


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
