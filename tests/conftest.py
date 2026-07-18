"""Shared pytest fixtures and test doubles."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient


class FakeProvider(LLMProvider):
    """A deterministic LLM provider for tests — never hits the network."""

    name = "fake"

    def __init__(self, reply: str = "Certainly, Sir.") -> None:
        super().__init__(api_key="test-key", model="fake-model")
        self.reply = reply
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages, system=None) -> LLMResult:  # type: ignore[override]
        self.calls.append(messages)
        return LLMResult(
            text=self.reply,
            model=self.model,
            provider=self.name,
            input_tokens=10,
            output_tokens=5,
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        llm_provider="anthropic",
        log_file="",  # no file handler in tests
    )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def engine(settings: Settings, fake_provider: FakeProvider) -> JarvisEngine:
    llm = LLMClient(primary=fake_provider)
    container = ServiceContainer(settings, llm_client=llm)
    return JarvisEngine(container=container)
