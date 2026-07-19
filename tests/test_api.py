"""Tests for the HTTP/WebSocket API (FastAPI TestClient, fake engine)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from jarvis.api.app import create_app  # noqa: E402
from jarvis.config.settings import Settings  # noqa: E402
from jarvis.core.container import ServiceContainer  # noqa: E402
from jarvis.core.engine import JarvisEngine  # noqa: E402
from jarvis.llm.client import LLMClient  # noqa: E402
from tests.conftest import FakeProvider  # noqa: E402


def _app(api_key: str = ""):
    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        api_key=api_key,
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    return create_app(engine=engine, settings=settings)


def test_root_and_health():
    with TestClient(_app()) as client:
        assert client.get("/").json()["name"] == "J.A.R.V.I.S."
        health = client.get("/health").json()
        assert "ok" in health and isinstance(health["checks"], list)


def test_chat_open_when_no_key():
    with TestClient(_app()) as client:
        resp = client.post("/chat", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Certainly, Sir."


def test_chat_requires_key_when_set():
    with TestClient(_app(api_key="secret")) as client:
        assert client.post("/chat", json={"message": "hi"}).status_code == 401
        ok = client.post("/chat", json={"message": "hi"},
                        headers={"Authorization": "Bearer secret"})
        assert ok.status_code == 200


def test_chat_accepts_x_api_key_header():
    with TestClient(_app(api_key="secret")) as client:
        resp = client.post("/chat", json={"message": "hi"},
                        headers={"X-API-Key": "secret"})
        assert resp.status_code == 200


def test_websocket_streams():
    import json

    with TestClient(_app()) as client:
        with client.websocket_connect("/ws/s1") as ws:
            ws.send_text("stream please")
            chunks = []
            while True:
                frame = ws.receive_text()
                try:
                    payload = json.loads(frame)
                except json.JSONDecodeError:
                    chunks.append(frame)
                    continue
                if isinstance(payload, dict) and payload.get("event") == "done":
                    break
                chunks.append(frame)
        assert "".join(chunks) == "Certainly, Sir."


def test_websocket_rejects_bad_key():
    from starlette.websockets import WebSocketDisconnect

    with TestClient(_app(api_key="secret")) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/s1") as ws:
                ws.receive_text()
