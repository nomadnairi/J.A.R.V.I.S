"""
Base classes for skills (plugins / tools).

A *skill* is a self-contained capability with two invocation paths:

1. **Fast path** — deterministic keyword matching via :meth:`can_handle`, then
   :meth:`handle`. Zero LLM cost; used for common intents ("what time is it").
2. **Tool path** — the LLM decides to call the skill as a tool. If the skill
   declares :attr:`parameters`, it is advertised to the model and invoked via
   :meth:`execute` with structured arguments.

A skill may support either or both paths. Both handlers are async so skills can
perform I/O (smart-home calls, HTTP, DB) in later stages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from jarvis.llm.tools import ToolSpec


@dataclass
class SkillResult:
    """The outcome of a skill handling a request."""

    text: str
    handled: bool = True
    metadata: dict = field(default_factory=dict)

    @classmethod
    def not_handled(cls) -> "SkillResult":
        return cls(text="", handled=False)


class BaseSkill(ABC):
    """Abstract base class for all skills."""

    #: Unique skill name (registry key, tool name, telemetry label).
    name: str = "base"
    #: Human-readable one-line description (shown to users and the model).
    description: str = ""
    #: Higher priority skills are matched first on the fast path (default 0).
    priority: int = 0
    #: JSON-Schema for tool arguments. ``None`` = not exposed to the LLM.
    parameters: dict | None = None

    # -- fast path ----------------------------------------------------------

    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """Return True if this skill wants to handle ``text`` directly."""
        raise NotImplementedError

    @abstractmethod
    async def handle(self, text: str, context: "dict | None" = None) -> SkillResult:
        """Produce a :class:`SkillResult` for raw ``text`` (fast path)."""
        raise NotImplementedError

    # -- tool path ----------------------------------------------------------

    async def execute(self, **kwargs: object) -> SkillResult:
        """Invoke the skill as an LLM tool with structured ``kwargs``.

        Default implementation ignores arguments and delegates to
        :meth:`handle`. Skills that take parameters should override this.
        """
        return await self.handle("", None)

    def as_tool_spec(self) -> ToolSpec | None:
        """Return a :class:`ToolSpec` if this skill is exposed as a tool."""
        if self.parameters is None:
            return None
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Skill {self.name!r} priority={self.priority}>"
