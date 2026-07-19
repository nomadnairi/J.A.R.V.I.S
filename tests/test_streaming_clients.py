"""Tests for /chat/stream and the streaming client paths."""

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


def _make(api_key: str = ""):
    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        api_key=api_key,
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    return create_app(engine=engine, settings=settings)


def test_chat_stream_returns_full_text():
    with TestClient(_make()) as client:
        with client.stream("POST", "/chat/stream",
                        json={"message": "hello"}) as resp:
            assert resp.status_code == 200
            body = "".join(chunk for chunk in resp.iter_text())
    assert body == "Certainly, Sir."


def test_chat_stream_requires_key_when_set():
    with TestClient(_make(api_key="secret")) as client:
        resp = client.post("/chat/stream", json={"message": "hi"})
        assert resp.status_code == 401
        with client.stream("POST", "/chat/stream", json={"message": "hi"},
                        headers={"Authorization": "Bearer secret"}) as ok:
            assert ok.status_code == 200
            assert "".join(ok.iter_text()) == "Certainly, Sir."


def test_api_client_chat_stream_against_real_server():
    import threading
    import time

    import uvicorn

    from jarvis.desktop_app.api_client import JarvisApiClient

    app = _make()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8766,
                                        log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    try:
        client = JarvisApiClient("http://127.0.0.1:8766")
        chunks: list[str] = []
        full = client.chat_stream("hello", on_chunk=chunks.append)
        assert full == "Certainly, Sir."
        assert "".join(chunks) == full
        assert chunks  # at least one chunk arrived through the callback
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_engine_thread_stream_async():
    import threading as _threading

    from jarvis.desktop_app.engine_thread import EngineThread

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
    )
    engine_thread = EngineThread(settings)

    def _run_with_fake():
        import asyncio
        engine_thread._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(engine_thread._loop)
        engine_thread._engine = JarvisEngine(container=ServiceContainer(
            settings, llm_client=LLMClient(primary=FakeProvider())))
        engine_thread._loop.run_until_complete(engine_thread._engine.start())
        engine_thread._started.set()
        engine_thread._loop.run_forever()
        engine_thread._loop.run_until_complete(engine_thread._engine.shutdown())
        engine_thread._loop.close()

    engine_thread._thread = _threading.Thread(target=_run_with_fake, daemon=True)
    engine_thread.start()
    try:
        chunks: list[str] = []
        errors: list = []
        done = _threading.Event()

        engine_thread.stream_async(
            "hello",
            on_chunk=chunks.append,
            on_done=lambda err: (errors.append(err), done.set()),
        )
        assert done.wait(30)
        assert errors == [None]
        assert "".join(chunks) == "Certainly, Sir."
    finally:
        engine_thread.stop()
