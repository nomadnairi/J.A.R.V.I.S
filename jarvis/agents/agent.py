"""
Autonomous sub-agent.

Runs its own multi-step LLM + tool loop to complete a single task, independent
of the main conversation. Reuses the shared LLM client and tool registry, so it
can do anything the assistant can — but focused on one goal.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.llm.client import LLMClient
from jarvis.llm.tools import ToolResult
from jarvis.skills.registry import SkillRegistry
from jarvis.utils.exceptions import JarvisError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM = (
    "You are an autonomous sub-agent of J.A.R.V.I.S. You are given a single "
    "task. Complete it by reasoning step by step and calling the available "
    "tools as needed. When the task is done, reply with the final result "
    "only — concise and directly useful."
)


@dataclass
class AgentResult:
    """The outcome of an agent run."""

    text: str
    steps: int
    tool_calls: int
    completed: bool  # False if it hit the step limit


class Agent:
    """A task-focused autonomous agent."""

    def __init__(
        self,
        llm: LLMClient,
        skills: SkillRegistry,
        *,
        max_steps: int = 8,
        exclude_tools: set[str] | None = None,
    ) -> None:
        self.llm = llm
        self.skills = skills
        self.max_steps = max_steps
        # Exclude run_agent by default to prevent unbounded self-delegation.
        self.exclude_tools = exclude_tools or {"run_agent"}

    async def run(self, task: str) -> AgentResult:
        """Work toward ``task`` and return the result."""
        tools = [t for t in self.skills.tool_specs()
                if t.name not in self.exclude_tools]
        messages: list[dict] = [{"role": "user", "content": task}]
        tool_calls = 0
        result = None

        for step in range(1, self.max_steps + 1):
            result = await self.llm.complete(messages, system=_SYSTEM, tools=tools)
            if not result.wants_tools:
                return AgentResult(result.text, step, tool_calls, completed=True)

            tool_results: list[ToolResult] = []
            for call in result.tool_calls:
                tool_calls += 1
                try:
                    sr = await self.skills.invoke_tool(call.name, call.arguments)
                    content, is_error = sr.text, False
                except JarvisError as exc:
                    content, is_error = f"Tool error: {exc}", True
                tool_results.append(
                    ToolResult(call_id=call.id, name=call.name, content=content,
                            is_error=is_error)
                )
            messages = messages + self.llm.continuation_messages(result, tool_results)

        logger.warning("Agent hit the step limit (%d) on task", self.max_steps)
        return AgentResult(
            result.text if result else "", self.max_steps, tool_calls, completed=False
        )
