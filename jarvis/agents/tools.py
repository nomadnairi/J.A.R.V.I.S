"""The ``run_agent`` tool — delegate a task to an autonomous sub-agent."""

from __future__ import annotations

from jarvis.agents.agent import Agent
from jarvis.llm.client import LLMClient
from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.skills.registry import SkillRegistry


class RunAgentSkill(BaseSkill):
    """Delegate a complex, multi-step task to an autonomous sub-agent."""

    name = "run_agent"
    description = (
        "Delegate a complex, multi-step task to an autonomous sub-agent that "
        "will use tools to complete it and return the result. Use this for "
        "tasks that need several steps (research, then act, then summarise)."
    )
    priority = 20
    parameters = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task for the sub-agent."}
        },
        "required": ["task"],
    }

    def __init__(self, llm: LLMClient, registry: SkillRegistry,
                max_steps: int = 8) -> None:
        # The registry is shared and fully populated by the time execute runs.
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()

    async def execute(self, task: str = "", **_: object) -> SkillResult:
        if not task.strip():
            return SkillResult(text="I need a task to delegate.")
        agent = Agent(self.llm, self.registry, max_steps=self.max_steps)
        result = await agent.run(task)
        prefix = "" if result.completed else "(reached step limit) "
        return SkillResult(
            text=prefix + result.text,
            metadata={"steps": result.steps, "tool_calls": result.tool_calls},
        )
