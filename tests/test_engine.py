"""End-to-end tests for the async engine (routing, tools, streaming, sessions)."""

from __future__ import annotations

import pytest

from jarvis.config.constants import AssistantState, ResponseType
from jarvis.models.response import Request
from tests.conftest import FakeProvider, build_engine, make_tool_call_result


@pytest.mark.asyncio
async def test_llm_path_returns_reply(engine):
    reply = await engine.ask("Tell me a story about the sea.")
    assert reply == "Certainly, Sir."


@pytest.mark.asyncio
async def test_skill_path_bypasses_llm(engine, fake_provider):
    # "system status" is handled by the SystemSkill, not the LLM.
    response = await engine.process(Request(text="system status"))
    assert response.type == ResponseType.SKILL
    assert response.source == "system_status"
    assert fake_provider.calls == []  # LLM never called


@pytest.mark.asyncio
async def test_llm_path_records_history(engine):
    await engine.ask("first")
    await engine.ask("second")
    session = engine.session("default")
    assert len(session.conversation) == 4  # 2 user + 2 assistant


@pytest.mark.asyncio
async def test_reset_clears_history(engine):
    await engine.ask("hello")
    assert len(engine.session("default").conversation) > 0
    await engine.reset("default")
    assert len(engine.session("default").conversation) == 0


@pytest.mark.asyncio
async def test_engine_returns_to_idle(engine):
    await engine.ask("anything")
    assert engine.state.state == AssistantState.IDLE


@pytest.mark.asyncio
async def test_telemetry_counts_requests(engine):
    await engine.ask("one")
    await engine.ask("two")
    stats = engine.stats
    assert stats["requests_total"] == 2
    assert stats["responses_total"] == 2


@pytest.mark.asyncio
async def test_telemetry_tracks_skill_by_name(engine):
    await engine.process(Request(text="system status"))
    await engine.process(Request(text="what time is it"))
    stats = engine.stats
    assert stats["skill_usage"].get("system_status") == 1
    assert stats["skill_usage"].get("get_datetime") == 1


# -- agentic tool loop ------------------------------------------------------


@pytest.mark.asyncio
async def test_agentic_tool_loop(settings):
    # First completion asks to call the calculator; second returns final text.
    provider = FakeProvider(
        default_reply="The answer is 40.",
        results=[make_tool_call_result("calculator", {"expression": "(12.5/100)*320"})],
    )
    engine = build_engine(settings, provider)

    response = await engine.process(Request(text="what is 12.5% of 320?"))

    assert response.type == ResponseType.LLM
    assert response.text == "The answer is 40."
    # Two completions: one requesting the tool, one producing the final answer.
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_tool_loop_stops_at_max_rounds(settings):
    # Provider always asks for a tool -> loop must terminate at max_tool_rounds.
    settings.max_tool_rounds = 3
    provider = FakeProvider(
        results=[make_tool_call_result("calculator", {"expression": "1+1"})] * 10
    )
    engine = build_engine(settings, provider)
    await engine.process(Request(text="loop forever"))
    assert len(provider.calls) == 3


# -- streaming --------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_llm_reply(engine):
    chunks = [c async for c in engine.stream(Request(text="stream me a poem"))]
    assert "".join(chunks) == "Certainly, Sir."


@pytest.mark.asyncio
async def test_stream_skill_reply_single_chunk(engine):
    chunks = [c async for c in engine.stream(Request(text="system status"))]
    assert len(chunks) == 1
    assert "Version" in chunks[0]


# -- multi-session ----------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_are_isolated(engine):
    await engine.ask("remember A", session_id="alice")
    await engine.ask("remember B", session_id="bob")
    assert len(engine.session("alice").conversation) == 2
    assert len(engine.session("bob").conversation) == 2
    # Different objects, no cross-contamination.
    assert engine.session("alice") is not engine.session("bob")
