"""
Logging setup for J.A.R.V.I.S.

Provides colourful console output via :mod:`rich` plus an optional rotating
log file. Call :func:`setup_logging` once at startup, then obtain named
loggers anywhere with :func:`get_logger`.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

_CONFIGURED = False


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure the root logger.

    Args:
        level: Minimum log level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        log_file: Optional path to a rotating log file. Parent directories are
            created automatically.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Console handler — rich, human-friendly.
    console = RichHandler(rich_tracebacks=True, show_path=False, markup=True)
    console.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    root.addHandler(console)

    # File handler — plain text, rotating.
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )
        root.addHandler(file_handler)

    # Quiet down noisy third-party libraries.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (e.g. ``get_logger(__name__)``)."""
    return logging.getLogger(name)
