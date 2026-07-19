"""
HTTP / WebSocket API for J.A.R.V.I.S.

A FastAPI app over the engine: a JSON ``/chat`` endpoint, a streaming
WebSocket, and a ``/health`` check — so desktop, mobile, or web clients can
talk to a JARVIS instance running on a server. Protected by an API key.

Run it with:

    python -m jarvis.api        # or: jarvis-api

``fastapi`` and ``uvicorn`` are optional dependencies.
"""

from jarvis.api.app import create_app

__all__ = ["create_app"]
