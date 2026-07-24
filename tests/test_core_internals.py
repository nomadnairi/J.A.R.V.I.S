"""Coverage tests for core internals that lack direct tests."""

from __future__ import annotations

import pytest

from jarvis.config.constants import AssistantState
from jarvis.core.context import SessionContext
from jarvis.core.pipeline import (
    LoggingMiddleware,
    Middleware,
    NormalizeMiddleware,
    Pipeline,
)
from jarvis.core.session import SessionManager
from jarvis.core.state import StateMachine
from jarvis.events.bus import EventBus
from jarvis.llm.prompts import PromptBuilder
from jarvis.models.message import Conversation
from jarvis.models.response import Request, Response
from jarvis.telemetry.metrics import MetricsCollector
from jarvis.utils.retry import retry_async
from jarvis.utils.text import normalize, strip_wake_word, truncate
from jarvis.utils.timing import measure


# -- pipeline ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_runs_middleware_in_order():
    order: list[str] = []

    class Tag(Middleware):
        def __init__(self, name):
            self.name = name

        async def process(self, request, next_):
            order.append(f"before:{self.name}")
            resp = await next_(request)
            order.append(f"after:{self.name}")
            return resp

    pipe = Pipeline([Tag("a"), Tag("b")])

    async def handler(req):
        order.append("handler")
        return Response(text="ok")

    await pipe.run(Request(text="x"), handler)
    assert order == ["before:a", "before:b", "handler", "after:b", "after:a"]


@pytest.mark.asyncio
async def test_normalize_middleware_collapses_whitespace():
    pipe = Pipeline([NormalizeMiddleware(), LoggingMiddleware()])
    seen: dict = {}

    async def handler(req):
        seen["text"] = req.text
        return Response(text="ok")

    await pipe.run(Request(text="  hi   there  "), handler)
    assert seen["text"] == "hi there"


# -- state machine ----------------------------------------------------------


@pytest.mark.asyncio
async def test_state_machine_valid_transition_emits_event():
    bus = EventBus()
    seen: list = []
    from jarvis.config.constants import EventType
    bus.subscribe(EventType.STATE_CHANGED, seen.append)
    sm = StateMachine(bus)
    await sm.transition(AssistantState.THINKING)
    assert sm.state == AssistantState.THINKING
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_state_machine_rejects_invalid_transition():
    sm = StateMachine()
    await sm.transition(AssistantState.SPEAKING)  # not allowed from IDLE
    assert sm.state == AssistantState.IDLE


# -- session manager --------------------------------------------------------


def test_session_manager_reuses_and_isolates():
    mgr = SessionManager()
    a1 = mgr.get_or_create("a")
    a2 = mgr.get_or_create("a")
    assert a1 is a2
    assert mgr.get_or_create("b") is not a1


def test_session_manager_lru_eviction():
    mgr = SessionManager(max_sessions=2)
    mgr.get_or_create("a")
    mgr.get_or_create("b")
    mgr.get_or_create("c")  # evicts "a"
    assert len(mgr) == 2
    assert mgr.get("a") is None


def test_session_manager_loader_populates():
    def loader(sid):
        conv = Conversation()
        conv.add_user("loaded")
        return conv

    mgr = SessionManager(loader=loader)
    ctx = mgr.get_or_create("x")
    assert len(ctx.conversation) == 1


# -- prompts ----------------------------------------------------------------


def test_prompt_builder_includes_persona_and_language():
    pb = PromptBuilder("KER", "Sir")
    prompt = pb.system_prompt(language="Russian", extra_context="Note: X")
    assert "KER" in prompt
    assert "reply to the user in Russian" in prompt
    assert "Note: X" in prompt


def test_prompt_builder_aliases_and_name_override():
    pb = PromptBuilder("KER", "Sir", aliases=["Jarvis"])
    prompt = pb.system_prompt()
    assert "KER" in prompt and "Jarvis" in prompt
    # A per-request name overrides the default (white-label).
    prompt2 = pb.system_prompt(assistant_name="Vesper")
    assert "You are Vesper" in prompt2


# -- context ----------------------------------------------------------------


def test_session_context_reset():
    ctx = SessionContext(session_id="s")
    ctx.conversation.add_user("hi")
    ctx.scratch["k"] = 1
    ctx.reset()
    assert ctx.turns() == 0
    assert ctx.scratch == {}


# -- telemetry --------------------------------------------------------------


def test_metrics_summary_after_records():
    m = MetricsCollector()
    m.record_response(source="fake", latency_ms=100.0, tokens=5)
    m.record_response(source="fake", latency_ms=200.0, tokens=7, via_skill=True)
    summary = m.summary()
    assert summary["responses_total"] == 2
    assert summary["total_tokens"] == 12
    assert summary["latency_ms"]["avg"] == 150.0


# -- utils ------------------------------------------------------------------


def test_text_helpers():
    assert normalize("  a   b ") == "a b"
    assert truncate("abcdef", 4) == "abc…"
    assert strip_wake_word("Jarvis, hello", ("jarvis",)) == "hello"


@pytest.mark.asyncio
async def test_retry_async_eventually_succeeds():
    calls = {"n": 0}

    @retry_async(attempts=3, base_delay=0.0, exceptions=(ValueError,))
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert await flaky() == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_measure_records_elapsed():
    with measure() as sw:
        pass
    assert sw.elapsed_ms >= 0.0
