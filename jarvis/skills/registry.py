"""
Skill registry and dispatcher.

Holds all registered skills and, for a given request, finds the
highest-priority skill that claims it. Registration is validated so two skills
cannot share a name.
"""

from __future__ import annotations

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.exceptions import (
    SkillExecutionError,
    SkillRegistrationError,
)
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class SkillRegistry:
    """Registers skills and dispatches requests to them."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    # -- registration -------------------------------------------------------

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._skills:
            raise SkillRegistrationError(
                f"A skill named {skill.name!r} is already registered."
            )
        self._skills[skill.name] = skill
        logger.debug("Registered skill %r (priority=%d)", skill.name, skill.priority)

    def register_many(self, skills: list[BaseSkill]) -> None:
        for skill in skills:
            self.register(skill)

    def unregister(self, name: str) -> None:
        self._skills.pop(name, None)

    # -- dispatch -----------------------------------------------------------

    def find(self, text: str) -> BaseSkill | None:
        """Return the highest-priority skill that can handle ``text``."""
        candidates = sorted(
            self._skills.values(), key=lambda s: s.priority, reverse=True
        )
        for skill in candidates:
            try:
                if skill.can_handle(text):
                    return skill
            except Exception:  # noqa: BLE001 - a broken matcher must not crash routing
                logger.exception("Skill %r raised in can_handle()", skill.name)
        return None

    def dispatch(self, text: str, context: dict | None = None) -> SkillResult:
        """Route ``text`` to a matching skill, if any.

        Returns ``SkillResult.not_handled()`` when no skill matches, so the
        caller can fall back to the LLM.
        """
        skill = self.find(text)
        if skill is None:
            return SkillResult.not_handled()
        try:
            return skill.handle(text, context)
        except Exception as exc:  # noqa: BLE001
            raise SkillExecutionError(
                f"Skill {skill.name!r} failed: {exc}",
                details={"skill": skill.name},
            ) from exc

    # -- introspection ------------------------------------------------------

    def all(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._skills)
