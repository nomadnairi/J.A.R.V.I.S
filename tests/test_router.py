"""Tests for the AI router (model-tier routing)."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.llm.client import LLMClient
from jarvis.models.response import Request
from jarvis.routing.router import AIRouter, ModelTier
from tests.conftest import FakeProvider


def _router(enabled=True) -> AIRouter:
    return AIRouter("fast-m", "strong-m", enabled=enabled, word_threshold=40)


def test_disabled_returns_none():
    assert _router(enabled=False).model_for("anything") is None


def test_simple_text_routes_fast():
    assert _router().model_for("hi there") == "fast-m"
    assert _router().tier("hi there") == ModelTier.FAST


def test_long_text_routes_strong():
    long_text = " ".join(["word"] * 50)
    assert _router().model_for(long_text) == "strong-m"


def test_reasoning_cue_routes_strong():
    assert _router().tier("explain why this happens") == ModelTier.STRONG


def test_code_routes_strong():
    assert _router().tier("```\ndef f(): pass\n```") == ModelTier.STRONG


def test_multiple_questions_route_strong():
    assert _router().tier("what is this? and how? ") == ModelTier.STRONG


def test_from_settings_defaults_to_base_model_when_empty():
    router = AIRouter.from_settings(
        Settings(llm_model="base-x", ai_router_enabled=True)
    )
    # Empty fast/strong fall back to the base model.
    assert router.fast_model == "base-x"
    assert router.strong_model == "base-x"


# -- engine integration -----------------------------------------------------


@pytest.mark.asyncio
async def test_engine_passes_routed_model():
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=False,
                        files_enabled=False, coding_enabled=False,
                        ai_router_enabled=True, llm_model_fast="fast-m",
                        llm_model_strong="strong-m")
    provider = FakeProvider(default_reply="ok")
    engine = JarvisEngine(
        container=ServiceContainer(settings, llm_client=LLMClient(primary=provider))
    )
    await engine.process(Request(text="explain the theory of relativity in depth"))
    assert provider.models[-1] == "strong-m"
