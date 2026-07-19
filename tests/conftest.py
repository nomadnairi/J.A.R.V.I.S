"""Shared pytest fixtures and test doubles."""

from __future__ import annotations

from typing import AsyncIterator

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient
from jarvis.llm.tools import ToolCall


class FakeProvider(LLMProvider):
    """A deterministic LLM provider for tests — never hits the network.

    Returns queued results in order (falling back to ``default_reply`` once the
    queue is empty), so a test can script a tool-calling round followed by a
    final text answer.
    """

    name = "fake"

    def __init__(self, default_reply: str = "Certainly, Sir.",
                results: list[LLMResult] | None = None) -> None:
        super().__init__(api_key="test-key", model="fake-model")
        self.default_reply = default_reply
        self._queue = list(results or [])
        self.calls: list[list[dict]] = []
        self.models: list[str | None] = []
        self.stream_chunks = ["Cer", "tainly, ", "Sir."]

    async def complete(self, messages, system=None, tools=None, model=None) -> LLMResult:  # type: ignore[override]
        self.calls.append(messages)
        self.models.append(model)
        if self._queue:
            return self._queue.pop(0)
        return LLMResult(
            text=self.default_reply,
            model=self.model,
            provider=self.name,
            input_tokens=10,
            output_tokens=5,
        )

    async def stream(self, messages, system=None) -> AsyncIterator[str]:  # type: ignore[override]
        for chunk in self.stream_chunks:
            yield chunk

    def continuation_messages(self, result, tool_results):  # type: ignore[override]
        return [
            {"role": "assistant", "content": f"[tool_use x{len(result.tool_calls)}]"},
            {"role": "user", "content": f"[tool_results x{len(tool_results)}]"},
        ]


def make_tool_call_result(tool_name: str, arguments: dict) -> LLMResult:
    """Build an LLMResult that asks to call ``tool_name``."""
    return LLMResult(
        text="",
        model="fake-model",
        provider="fake",
        tool_calls=[ToolCall(id="call_1", name=tool_name, arguments=arguments)],
        stop_reason="tool_use",
        output_tokens=3,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        llm_provider="anthropic",
        log_file="",  # no file handler in tests
        memory_enabled=False,  # keep the default engine off disk
        integrations_enabled=False,  # no network at construction
        goals_enabled=False,  # no disk writes in the default engine
        rate_limit_enabled=False,  # deterministic tests
    )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


def build_engine(settings: Settings, provider: LLMProvider) -> JarvisEngine:
    llm = LLMClient(primary=provider)
    container = ServiceContainer(settings, llm_client=llm)
    return JarvisEngine(container=container)


@pytest.fixture
def engine(settings: Settings, fake_provider: FakeProvider) -> JarvisEngine:
    return build_engine(settings, fake_provider)
