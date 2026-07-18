"""Tests for the LLM client's retry and fallback behaviour."""

from __future__ import annotations

import pytest

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient
from jarvis.utils.exceptions import AllProvidersFailedError, LLMRequestError


class _AlwaysFails(LLMProvider):
    name = "always_fails"

    def __init__(self):
        super().__init__(api_key="k", model="m")
        self.attempts = 0

    def complete(self, messages, system=None):
        self.attempts += 1
        raise LLMRequestError("nope")


class _Works(LLMProvider):
    name = "works"

    def __init__(self):
        super().__init__(api_key="k", model="m")

    def complete(self, messages, system=None):
        return LLMResult(text="ok", model="m", provider=self.name)


def test_fallback_used_when_primary_fails():
    primary = _AlwaysFails()
    client = LLMClient(primary=primary, fallbacks=[_Works()], retry_attempts=1)
    result = client.complete([{"role": "user", "content": "hi"}])
    assert result.text == "ok"
    assert result.provider == "works"


def test_all_providers_failing_raises():
    client = LLMClient(primary=_AlwaysFails(), fallbacks=[_AlwaysFails()],
                    retry_attempts=1)
    with pytest.raises(AllProvidersFailedError):
        client.complete([{"role": "user", "content": "hi"}])


def test_retry_attempts_are_made():
    primary = _AlwaysFails()
    client = LLMClient(primary=primary, retry_attempts=3)
    with pytest.raises(AllProvidersFailedError):
        client.complete([{"role": "user", "content": "hi"}])
    assert primary.attempts == 3


def test_unavailable_provider_skipped():
    class _NoKey(_Works):
        name = "nokey"

        def __init__(self):
            super().__init__()
            self.api_key = ""  # not available

    client = LLMClient(primary=_NoKey(), fallbacks=[_Works()], retry_attempts=1)
    result = client.complete([{"role": "user", "content": "hi"}])
    assert result.provider == "works"
