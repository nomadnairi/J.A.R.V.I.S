"""Tests for the autonomous agent system."""

from __future__ import annotations

import pytest

from jarvis.agents.agent import Agent
from jarvis.agents.tools import RunAgentSkill
from jarvis.llm.client import LLMClient
from jarvis.skills.builtin.calculator_skill import CalculatorSkill
from jarvis.skills.registry import SkillRegistry
from tests.conftest import FakeProvider, make_tool_call_result


def _registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(CalculatorSkill())
    return reg


@pytest.mark.asyncio
async def test_agent_completes_without_tools():
    provider = FakeProvider(default_reply="Task complete.")
    agent = Agent(LLMClient(primary=provider), _registry())
    result = await agent.run("say something")
    assert result.completed is True
    assert result.text == "Task complete."
    assert result.tool_calls == 0


@pytest.mark.asyncio
async def test_agent_uses_a_tool_then_finishes():
    provider = FakeProvider(
        default_reply="The answer is 4.",
        results=[make_tool_call_result("calculator", {"expression": "2+2"})],
    )
    agent = Agent(LLMClient(primary=provider), _registry())
    result = await agent.run("compute 2+2")
    assert result.completed is True
    assert result.tool_calls == 1
    assert result.text == "The answer is 4."


@pytest.mark.asyncio
async def test_agent_respects_step_limit():
    # Provider always asks for a tool -> never finishes -> hits the limit.
    provider = FakeProvider(
        results=[make_tool_call_result("calculator", {"expression": "1+1"})] * 20
    )
    agent = Agent(LLMClient(primary=provider), _registry(), max_steps=3)
    result = await agent.run("loop")
    assert result.completed is False
    assert result.steps == 3


@pytest.mark.asyncio
async def test_agent_excludes_run_agent_tool():
    reg = _registry()
    provider = FakeProvider(default_reply="done")
    reg.register(RunAgentSkill(LLMClient(primary=provider), reg))
    agent = Agent(LLMClient(primary=provider), reg)
    # run_agent must not be offered to the sub-agent (no infinite delegation).
    tools = [t for t in reg.tool_specs() if t.name not in agent.exclude_tools]
    assert all(t.name != "run_agent" for t in tools)


@pytest.mark.asyncio
async def test_run_agent_tool_delegates():
    provider = FakeProvider(default_reply="Sub-agent done.")
    reg = _registry()
    skill = RunAgentSkill(LLMClient(primary=provider), reg)
    result = await skill.execute(task="do the thing")
    assert result.text == "Sub-agent done."
