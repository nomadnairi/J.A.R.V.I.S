"""Run the API server: ``python -m jarvis.api`` (or ``jarvis-api``)."""

from __future__ import annotations

import sys

from jarvis.config.settings import get_settings
from jarvis.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def main() -> int:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - optional dependency
        logger.error("The API needs 'uvicorn'. Install: pip install 'uvicorn[standard]'")
        return 1

    if not settings.api_key:
        logger.warning("API_KEY is not set — the API is OPEN. Set it before "
                    "exposing the server publicly.")

    from jarvis.api.app import create_app

    logger.info("Starting J.A.R.V.I.S. API on %s:%d", settings.api_host,
                settings.api_port)
    uvicorn.run(create_app(settings=settings), host=settings.api_host,
                port=settings.api_port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
