"""Run the desktop app: ``python -m jarvis.desktop_app`` (or ``jarvis-desktop``)."""

from __future__ import annotations

import sys

from jarvis.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def main() -> int:
    setup_logging(level="INFO", log_file="logs/jarvis.log")
    try:
        from jarvis.desktop_app.app import run_app
        return run_app()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
