"""OpenNode FastAPI server."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import settings
from .utils import check_gpu


def _initialize_storage_dir() -> Path:
    """Create the data directory structure if it does not exist."""
    data_dir = Path(settings.data_dir).expanduser().resolve()
    for subdir in ("audio", "models", "db"):
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
    return data_dir


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    logger.info(f"OpenNode backend starting on {settings.host}:{settings.port}")
    logger.info(f"ASR engine: {settings.asr_engine}")
    logger.info(f"Diarization: {settings.enable_diarization}")

    # Initialize storage directories
    data_dir = _initialize_storage_dir()
    logger.info(f"Data directory: {data_dir}")

    # Log GPU info at startup
    gpu_info = check_gpu()
    if gpu_info["available"]:
        logger.info(f"GPU detected: {gpu_info['name']} ({gpu_info['vram_mb']} MB VRAM)")
    else:
        logger.info("No CUDA GPU detected — running on CPU")

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
