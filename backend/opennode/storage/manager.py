"""Data directory manager for the OpenNode application."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from .database import Database


class DataManager:
    """Manages the ~/.opennode data directory and database lifecycle.

    Responsible for:
    - Creating the required directory structure on first run
    - Initialising and closing the async SQLite database
    - Reporting disk usage statistics
    - Cleaning up old audio files
    """

    def __init__(self, data_dir: str = "~/.opennode") -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.db_path = self.data_dir / "db" / "opennode.db"
        self.audio_dir = self.data_dir / "audio"
        self.models_dir = self.data_dir / "models"
        self.db = Database(self.db_path)

    def initialize_dirs(self) -> None:
        """Create the full directory structure if it does not exist."""
        for directory in [
            self.data_dir,
            self.audio_dir,
            self.models_dir,
            self.db_path.parent,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize directories and the database (create tables)."""
        self.initialize_dirs()
        await self.db.initialize()

    def get_storage_usage(self) -> dict:  # type: ignore[type-arg]
        """Return disk usage in bytes broken down by category.

        Returns
        -------
        dict with keys: ``audio_bytes``, ``db_bytes``, ``model_bytes``, ``total_bytes``
        """

        def _dir_size(path: Path) -> int:
            """Recursively sum file sizes in a directory."""
            if not path.exists():
                return 0
            total = 0
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except OSError:
                        pass
            return total

        audio_bytes = _dir_size(self.audio_dir)
        db_bytes = _dir_size(self.db_path.parent)
        model_bytes = _dir_size(self.models_dir)

        return {
            "audio_bytes": audio_bytes,
            "db_bytes": db_bytes,
            "model_bytes": model_bytes,
            "total_bytes": audio_bytes + db_bytes + model_bytes,
        }

    def cleanup_old_audio(self, max_age_days: int = 30) -> int:
        """Delete audio files older than ``max_age_days`` days.

        Parameters
        ----------
        max_age_days:
            Files with a modification time older than this many days are removed.

        Returns
        -------
        Number of files deleted.
        """
        if not self.audio_dir.exists():
            return 0

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        deleted = 0

        for entry in self.audio_dir.rglob("*"):
            if not entry.is_file():
                continue
            try:
                mtime = datetime.utcfromtimestamp(entry.stat().st_mtime)
                if mtime < cutoff:
                    entry.unlink()
                    deleted += 1
            except OSError:
                pass

        return deleted

    async def close(self) -> None:
        """Close the database connection."""
        await self.db.close()
