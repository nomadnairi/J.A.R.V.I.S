"""End-to-end tests for the engine (skills-first routing, LLM fallback)."""

from __future__ import annotations

from jarvis.config.constants import AssistantState, ResponseType
from jarvis.models.response import Request


def test_llm_path_returns_reply(engine):
    reply = engine.ask("Tell me a story about the sea.")
    assert reply == "Certainly, Sir."


def test_skill_path_bypasses_llm(engine, fake_provider):
    # "system status" is handled by the SystemSkill, not the LLM.
    response = engine.process(Request(text="system status"))
    assert response.type == ResponseType.SKILL
    assert response.source == "system"
    assert fake_provider.calls == []  # LLM never called


def test_llm_path_records_history(engine):
    engine.ask("first")
    engine.ask("second")
    # 2 user + 2 assistant messages
    assert len(engine.session.conversation) == 4


def test_reset_clears_history(engine):
    engine.ask("hello")
    assert len(engine.session.conversation) > 0
    engine.reset()
    assert len(engine.session.conversation) == 0


def test_engine_returns_to_idle(engine):
    engine.ask("anything")
    assert engine.state.state == AssistantState.IDLE


def test_telemetry_counts_requests(engine):
    engine.ask("one")
    engine.ask("two")
    stats = engine.stats
    assert stats["requests_total"] == 2
    assert stats["responses_total"] == 2


def test_skill_response_has_zero_llm_tokens(engine):
    response = engine.process(Request(text="what time is it"))
    assert response.type == ResponseType.SKILL
    assert response.tokens == 0


def test_telemetry_tracks_skill_by_name(engine):
    engine.process(Request(text="system status"))
    engine.process(Request(text="what time is it"))
    stats = engine.stats
    assert stats["skill_usage"].get("system") == 1
    assert stats["skill_usage"].get("datetime") == 1


def test_telemetry_tracks_provider_for_llm(engine):
    engine.ask("something the LLM must answer")
    stats = engine.stats
    assert stats["provider_usage"].get("fake") == 1
