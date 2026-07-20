"""Tests for /models and per-request model/language on chat."""

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


def _app():
    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        api_key="",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider(),
                                    profiles={"claude": FakeProvider()})))
    return create_app(engine=engine, settings=settings), engine


def test_models_lists_profiles():
    app, _ = _app()
    with TestClient(app) as client:
        out = client.get("/models").json()
        assert out == {"models": ["claude"]}


def test_chat_applies_model_and_language():
    app, engine = _app()
    with TestClient(app) as client:
        resp = client.post("/chat", json={
            "message": "hi", "session_id": "s1",
            "model": "claude", "language": "ru",
        })
        assert resp.status_code == 200
        scratch = engine.session("shared::s1").scratch
        assert scratch["model_profile"] == "claude"
        assert scratch["language"] == "ru"


def test_chat_without_prefs_leaves_scratch_untouched():
    app, engine = _app()
    with TestClient(app) as client:
        client.post("/chat", json={"message": "hi", "session_id": "s2"})
        scratch = engine.session("shared::s2").scratch
        assert "model_profile" not in scratch
