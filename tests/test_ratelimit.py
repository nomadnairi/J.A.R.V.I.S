"""Tests for rate limiting."""

from __future__ import annotations

import pytest

from jarvis.config.constants import ResponseType
from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.core.pipeline import Pipeline, RateLimitMiddleware
from jarvis.core.ratelimit import RateLimiter
from jarvis.llm.client import LLMClient
from jarvis.models.response import Request, Response
from tests.conftest import FakeProvider


def test_bucket_allows_up_to_capacity():
    limiter = RateLimiter(capacity=3, window_seconds=1000)
    assert [limiter.allow("k") for _ in range(4)] == [True, True, True, False]


def test_buckets_are_per_key():
    limiter = RateLimiter(capacity=1, window_seconds=1000)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True  # different key, own bucket
    assert limiter.allow("a") is False


def test_refill_over_time():
    limiter = RateLimiter(capacity=1, window_seconds=1000)
    limiter.allow("k")
    assert limiter.allow("k") is False
    # Force a refill by rewinding the bucket's timestamp.
    limiter._buckets["k"].updated -= 2000
    assert limiter.allow("k") is True


@pytest.mark.asyncio
async def test_middleware_blocks_when_over_limit():
    pipe = Pipeline([RateLimitMiddleware(RateLimiter(capacity=1, window_seconds=1000))])

    async def handler(req):
        return Response(text="ok", request_id=req.request_id)

    first = await pipe.run(Request(text="hi", session_id="s"), handler)
    second = await pipe.run(Request(text="hi", session_id="s"), handler)
    assert first.text == "ok"
    assert second.type == ResponseType.SYSTEM
    assert "slow down" in second.text


@pytest.mark.asyncio
async def test_engine_rate_limits():
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=False,
                        rate_limit_enabled=True, rate_limit_capacity=1,
                        rate_limit_window_seconds=1000)
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    r1 = await engine.process(Request(text="one", session_id="u"))
    r2 = await engine.process(Request(text="two", session_id="u"))
    assert r1.text == "Certainly, Sir."
    assert r2.source == "ratelimit"
