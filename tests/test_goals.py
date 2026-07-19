"""Tests for the goal system."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.core.runtime import set_session
from jarvis.goals.manager import GoalManager
from jarvis.goals.models import GoalStatus
from jarvis.goals.store import SQLiteGoalStore
from jarvis.goals.tools import AddGoalSkill, ListGoalsSkill, goal_skills
from jarvis.llm.client import LLMClient
from jarvis.models.response import Request
from tests.conftest import FakeProvider, make_tool_call_result


def _manager() -> GoalManager:
    return GoalManager(SQLiteGoalStore(":memory:"))


# -- manager ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_and_list_goals():
    mgr = _manager()
    g = await mgr.add("s", "Finish the report")
    assert g.id > 0
    active = await mgr.active("s")
    assert len(active) == 1 and active[0].text == "Finish the report"


@pytest.mark.asyncio
async def test_complete_goal():
    mgr = _manager()
    g = await mgr.add("s", "Call the bank")
    assert await mgr.complete("s", g.id) is True
    assert await mgr.active("s") == []
    done = await mgr.list("s", GoalStatus.DONE)
    assert len(done) == 1


@pytest.mark.asyncio
async def test_goals_isolated_by_session():
    mgr = _manager()
    await mgr.add("alice", "A")
    await mgr.add("bob", "B")
    assert len(await mgr.active("alice")) == 1
    assert len(await mgr.active("bob")) == 1


@pytest.mark.asyncio
async def test_complete_missing_goal_returns_false():
    mgr = _manager()
    assert await mgr.complete("s", 999) is False


# -- tools (session from context var) --------------------------------------


@pytest.mark.asyncio
async def test_goal_tools_use_current_session():
    mgr = _manager()
    add, list_ = AddGoalSkill(mgr), ListGoalsSkill(mgr)

    set_session("user-1")
    await add.execute(goal="Learn Uzbek")
    result = await list_.execute()
    assert "Learn Uzbek" in result.text

    # A different session sees no goals.
    set_session("user-2")
    assert "no open goals" in (await list_.execute()).text.lower()


def test_goal_skills_are_tools_not_fast_path():
    for skill in goal_skills(_manager()):
        assert skill.parameters is not None      # exposed as a tool
        assert skill.can_handle("anything") is False


@pytest.mark.asyncio
async def test_complete_goal_rejects_garbage_id():
    from jarvis.goals.tools import CompleteGoalSkill

    skill = CompleteGoalSkill(_manager())
    # A model sending a non-numeric id must not crash the tool.
    result = await skill.execute(goal_id="not-a-number")
    assert "valid goal number" in result.text


# -- engine end-to-end ------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_llm_adds_goal_via_tool():
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=True,
                        memory_db_path=":memory:")
    provider = FakeProvider(
        default_reply="I'll remember that goal.",
        results=[make_tool_call_result("add_goal", {"goal": "Ship v1"})],
    )
    engine = JarvisEngine(
        container=ServiceContainer(settings, llm_client=LLMClient(primary=provider))
    )
    await engine.process(Request(text="remind me to ship v1", session_id="u"))
    goals = await engine.goals.active("u")
    assert any("Ship v1" in g.text for g in goals)


@pytest.mark.asyncio
async def test_open_goals_injected_into_prompt():
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=True,
                        memory_db_path=":memory:")
    provider = FakeProvider(default_reply="Understood.")
    engine = JarvisEngine(
        container=ServiceContainer(settings, llm_client=LLMClient(primary=provider))
    )
    await engine.goals.add("u", "Water the plants")

    captured: dict = {}
    original = provider.complete

    async def spy(messages, system=None, tools=None, model=None):
        captured["system"] = system
        return await original(messages, system, tools)

    provider.complete = spy  # type: ignore[assignment]
    await engine.process(Request(text="hi", session_id="u"))
    assert "Water the plants" in (captured.get("system") or "")
