"""OpenNode configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENNODE_", env_file=".env")

    # Server
    host: str = "127.0.0.1"
    port: int = 8765

    # ASR
    asr_engine: str = "parakeet"  # "parakeet" | "whisper" | "onnx"
    model_path: str = ""  # auto-download if empty
    language: str = "auto"

    # Audio
    sample_rate: int = 16000
    chunk_duration_ms: int = 200
    vad_threshold: float = 0.5

    # Diarization
    enable_diarization: bool = True
    max_speakers: int = 10

    # Summarization
    enable_summarization: bool = True
    summarization_provider: str = "ollama"  # "ollama" | "api"
    ollama_model: str = "llama3.2"
    ollama_url: str = "http://localhost:11434"

    # Storage
    data_dir: str = "~/.opennode"

    # Logging
    log_level: str = "INFO"
    log_file: str = ""  # empty = no file logging


settings = Settings()
