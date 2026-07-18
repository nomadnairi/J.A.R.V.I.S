"""
Base classes for skills (plugins).

A *skill* is a self-contained capability that can:
  1. decide whether it can handle a given request (:meth:`BaseSkill.can_handle`), and
  2. produce a response for it (:meth:`BaseSkill.handle`).

Skills are matched by :class:`~jarvis.skills.registry.SkillRegistry` in
priority order. If none match, the engine falls back to the LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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

    #: Unique skill name (used for registry keys and telemetry).
    name: str = "base"
    #: Human-readable one-line description (shown by the help skill).
    description: str = ""
    #: Higher priority skills are matched first (default 0).
    priority: int = 0

    @abstractmethod
    def can_handle(self, text: str) -> bool:
        """Return True if this skill wants to handle ``text``."""
        raise NotImplementedError

    @abstractmethod
    def handle(self, text: str, context: "dict | None" = None) -> SkillResult:
        """Produce a :class:`SkillResult` for ``text``."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Skill {self.name!r} priority={self.priority}>"
