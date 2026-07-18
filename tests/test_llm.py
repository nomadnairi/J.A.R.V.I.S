"""Tests for the async LLM client's retry, fallback and streaming."""

from __future__ import annotations

from typing import AsyncIterator

import pytest

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient
from jarvis.utils.exceptions import AllProvidersFailedError, LLMRequestError


class _AlwaysFails(LLMProvider):
    name = "always_fails"

    def __init__(self):
        super().__init__(api_key="k", model="m")
        self.attempts = 0

    async def complete(self, messages, system=None, tools=None):
        self.attempts += 1
        raise LLMRequestError("nope")

    async def stream(self, messages, system=None) -> AsyncIterator[str]:
        raise LLMRequestError("nope")
        yield ""  # pragma: no cover

    def continuation_messages(self, result, tool_results):
        return []


class _Works(LLMProvider):
    name = "works"

    def __init__(self):
        super().__init__(api_key="k", model="m")

    async def complete(self, messages, system=None, tools=None):
        return LLMResult(text="ok", model="m", provider=self.name)

    async def stream(self, messages, system=None) -> AsyncIterator[str]:
        for chunk in ("he", "llo"):
            yield chunk

    def continuation_messages(self, result, tool_results):
        return []


@pytest.mark.asyncio
async def test_fallback_used_when_primary_fails():
    client = LLMClient(primary=_AlwaysFails(), fallbacks=[_Works()], retry_attempts=1)
    result = await client.complete([{"role": "user", "content": "hi"}])
    assert result.text == "ok"
    assert result.provider == "works"


@pytest.mark.asyncio
async def test_all_providers_failing_raises():
    client = LLMClient(primary=_AlwaysFails(), fallbacks=[_AlwaysFails()],
                    retry_attempts=1)
    with pytest.raises(AllProvidersFailedError):
        await client.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_retry_attempts_are_made():
    primary = _AlwaysFails()
    client = LLMClient(primary=primary, retry_attempts=3)
    with pytest.raises(AllProvidersFailedError):
        await client.complete([{"role": "user", "content": "hi"}])
    assert primary.attempts == 3


@pytest.mark.asyncio
async def test_unavailable_provider_skipped():
    class _NoKey(_Works):
        name = "nokey"

        def __init__(self):
            super().__init__()
            self.api_key = ""  # not available

    client = LLMClient(primary=_NoKey(), fallbacks=[_Works()], retry_attempts=1)
    result = await client.complete([{"role": "user", "content": "hi"}])
    assert result.provider == "works"


@pytest.mark.asyncio
async def test_stream_yields_chunks():
    client = LLMClient(primary=_Works())
    chunks = [c async for c in client.stream([{"role": "user", "content": "hi"}])]
    assert "".join(chunks) == "hello"


@pytest.mark.asyncio
async def test_stream_falls_back_before_first_chunk():
    client = LLMClient(primary=_AlwaysFails(), fallbacks=[_Works()])
    chunks = [c async for c in client.stream([{"role": "user", "content": "hi"}])]
    assert "".join(chunks) == "hello"
