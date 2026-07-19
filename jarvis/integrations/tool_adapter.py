"""
Bridge integration actions into the skill/tool system.

Each :class:`~jarvis.integrations.base.IntegrationAction` is wrapped in an
:class:`IntegrationToolSkill` and registered in the
:class:`~jarvis.skills.registry.SkillRegistry`. This means integrations are
exposed to the LLM through the exact same tool-calling machinery as built-in
skills — no special-casing in the engine.
"""

from __future__ import annotations

from jarvis.integrations.base import IntegrationAction
from jarvis.skills.base import BaseSkill, SkillResult


class IntegrationToolSkill(BaseSkill):
    """Adapts an :class:`IntegrationAction` to the :class:`BaseSkill` interface.

    These are tool-only skills: ``can_handle`` always returns False, so they
    never trigger on the fast keyword path — they are invoked only when the LLM
    decides to call the tool.
    """

    priority = 30

    def __init__(self, action: IntegrationAction) -> None:
        self._action = action
        self.name = action.name
        self.description = action.description
        self.parameters = action.parameters

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        # Not reachable via the fast path; provided for completeness.
        return SkillResult.not_handled()

    async def execute(self, **kwargs: object) -> SkillResult:
        result = await self._action.handler(**kwargs)
        return SkillResult(text=str(result))
