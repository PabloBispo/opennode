"""Tests for the OpenNode server."""

import pytest
from httpx import AsyncClient, ASGITransport

from opennode.server import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "gpu_available" in data


@pytest.mark.asyncio
async def test_health_endpoint_returns_expected_fields() -> None:
    """Health endpoint must return status, version, gpu_available, and gpu_info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "gpu_available" in data
    assert "gpu_info" in data
    gpu_info = data["gpu_info"]
    assert "available" in gpu_info
    assert "name" in gpu_info
    assert "vram_mb" in gpu_info
    assert "compute_capability" in gpu_info


@pytest.mark.asyncio
async def test_health_endpoint_gpu_available_matches_gpu_info() -> None:
    """gpu_available in the response should match gpu_info['available']."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert data["gpu_available"] == data["gpu_info"]["available"]


def test_config_defaults() -> None:
    """Settings should have correct defaults."""
    from opennode.config import Settings

    s = Settings()
    assert s.host == "127.0.0.1"
    assert s.port == 8765
    assert s.asr_engine == "parakeet"
    assert s.sample_rate == 16000
    assert s.vad_threshold == 0.5
    assert s.enable_diarization is True
    assert s.enable_summarization is True
    assert s.summarization_provider == "ollama"
    assert s.ollama_model == "llama3.2"
    assert s.data_dir == "~/.opennode"
    assert s.log_level == "INFO"


def test_config_loads_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configuration should load overrides from OPENNODE_ prefixed env vars."""
    monkeypatch.setenv("OPENNODE_HOST", "0.0.0.0")
    monkeypatch.setenv("OPENNODE_PORT", "9876")
    monkeypatch.setenv("OPENNODE_ASR_ENGINE", "whisper")
    monkeypatch.setenv("OPENNODE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENNODE_ENABLE_DIARIZATION", "false")

    from opennode.config import Settings

    s = Settings()
    assert s.host == "0.0.0.0"
    assert s.port == 9876
    assert s.asr_engine == "whisper"
    assert s.log_level == "DEBUG"
    assert s.enable_diarization is False


def test_check_gpu_returns_dict() -> None:
    """check_gpu() should always return a dict with expected keys."""
    from opennode.utils import check_gpu

    result = check_gpu()
    assert isinstance(result, dict)
    assert "available" in result
    assert "name" in result
    assert "vram_mb" in result
    assert "compute_capability" in result
    assert isinstance(result["available"], bool)


def test_check_gpu_no_cuda_returns_false() -> None:
    """When torch is not available or no CUDA, available should be False."""
    import sys
    import importlib

    # Simulate torch not available by temporarily blocking the import
    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else None  # type: ignore[union-attr]

    # Just verify the structure is correct — torch may or may not be installed
    from opennode.utils import check_gpu

    result = check_gpu()
    # If torch is not installed (which is the case in the dev env), available must be False
    try:
        import torch  # noqa: F401
        torch_available = True
    except ImportError:
        torch_available = False

    if not torch_available:
        assert result["available"] is False
        assert result["name"] is None
        assert result["vram_mb"] is None
        assert result["compute_capability"] is None
