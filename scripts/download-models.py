#!/usr/bin/env python3
"""Pre-download ASR models to ~/.opennode/models/.

Run this script once before starting OpenNode to avoid cold-start delays.
All downloads are idempotent — models already present are skipped.

Usage
-----
    python scripts/download-models.py [--engine parakeet|whisper|onnx|all]

Exit codes
----------
    0 — all requested models downloaded (or already present)
    1 — at least one model failed to download
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

MODELS_DIR = Path("~/.opennode/models").expanduser()
PARAKEET_MODEL = "nvidia/parakeet-tdt-0.6b-v3"
WHISPER_MODEL = "large-v3"


def _print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_ok(msg: str) -> None:
    print(f"[OK]  {msg}")


def _print_skip(msg: str) -> None:
    print(f"[--]  {msg}")


def _print_fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


def download_parakeet_nemo() -> bool:
    """Download the Parakeet model via NeMo.

    Returns:
        True if successful, False otherwise.
    """
    _print_header("Parakeet TDT 0.6B v3 (NeMo / GPU)")

    try:
        import nemo.collections.asr as nemo_asr  # type: ignore[import-untyped]
    except ImportError:
        _print_fail(
            "NeMo is not installed. "
            "Install with: pip install 'opennode-backend[gpu]'"
        )
        return False

    try:
        print(f"  Downloading '{PARAKEET_MODEL}' …")
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model = nemo_asr.models.ASRModel.from_pretrained(PARAKEET_MODEL)
        del model
        _print_ok(f"Parakeet model ready at ~/.opennode/models/")
        return True
    except Exception as exc:
        _print_fail(f"Failed to download Parakeet NeMo model: {exc}")
        return False


def download_parakeet_onnx() -> bool:
    """Download the ONNX-quantised Parakeet model.

    Returns:
        True if successful, False otherwise.
    """
    _print_header("Parakeet TDT 0.6B v3 (ONNX / CPU, INT8 ~640 MB)")

    try:
        from onnx_asr import Parakeet  # type: ignore[import-untyped]
    except ImportError:
        _print_fail(
            "onnx-asr is not installed. "
            "Install with: pip install 'opennode-backend[cpu]'"
        )
        return False

    try:
        print(f"  Downloading '{PARAKEET_MODEL}' (ONNX INT8) …")
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        # Instantiating Parakeet triggers the download.
        model = Parakeet(model=PARAKEET_MODEL, cache_dir=str(MODELS_DIR))  # type: ignore[call-arg]
        del model
        _print_ok("ONNX Parakeet model ready.")
        return True
    except Exception as exc:
        _print_fail(f"Failed to download ONNX Parakeet model: {exc}")
        return False


def download_whisper() -> bool:
    """Download the faster-whisper large-v3 model.

    Returns:
        True if successful, False otherwise.
    """
    _print_header(f"Whisper {WHISPER_MODEL} (faster-whisper, ~3 GB)")

    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    except ImportError:
        _print_fail(
            "faster-whisper is not installed. "
            "Install with: pip install 'opennode-backend[whisper]'"
        )
        return False

    whisper_cache = MODELS_DIR / "whisper"
    whisper_cache.mkdir(parents=True, exist_ok=True)

    try:
        print(f"  Downloading Whisper '{WHISPER_MODEL}' to {whisper_cache} …")
        # Instantiating WhisperModel with download_root triggers the download.
        model = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            download_root=str(whisper_cache),
        )
        del model
        _print_ok(f"Whisper model ready at {whisper_cache}/")
        return True
    except Exception as exc:
        _print_fail(f"Failed to download Whisper model: {exc}")
        return False


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Pre-download ASR models for OpenNode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--engine",
        choices=["parakeet", "whisper", "onnx", "all"],
        default="all",
        help=(
            "Which model(s) to download. "
            "'parakeet' downloads the NeMo GPU model, "
            "'onnx' downloads the CPU-only INT8 ONNX model, "
            "'whisper' downloads faster-whisper large-v3, "
            "'all' attempts all three. Default: all."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Entry point.

    Returns:
        Exit code — 0 on full success, 1 if any download failed.
    """
    args = parse_args()

    print(f"\nOpenNode model downloader")
    print(f"Model cache directory: {MODELS_DIR}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    results: list[bool] = []

    engine = args.engine

    if engine in ("parakeet", "all"):
        results.append(download_parakeet_nemo())

    if engine in ("onnx", "all"):
        results.append(download_parakeet_onnx())

    if engine in ("whisper", "all"):
        results.append(download_whisper())

    # Summary
    _print_header("Summary")
    successes = sum(1 for r in results if r)
    failures = len(results) - successes

    if failures == 0:
        print(f"All {successes} model(s) downloaded successfully.")
        print("\nYou can now start OpenNode.")
        return 0
    else:
        print(
            f"{successes}/{len(results)} model(s) downloaded. "
            f"{failures} failed — see errors above."
        )
        if failures == len(results):
            print(
                "\nNo models were downloaded. "
                "Make sure you have installed the relevant optional dependencies."
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
