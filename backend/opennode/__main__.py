"""OpenNode backend entry point."""

from __future__ import annotations

import sys
from loguru import logger
import uvicorn

from .config import settings


def setup_logging() -> None:
    """Configure loguru logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
        )


def main() -> None:
    setup_logging()
    logger.info("Starting OpenNode backend")
    uvicorn.run(
        "opennode.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
