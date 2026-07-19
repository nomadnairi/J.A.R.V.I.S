"""
Goal tools — expose the goal system to the LLM.

These are tool-only skills (never matched on the fast path). They read the
active session from the runtime context var, so each user's goals stay separate
without threading the session id through tool signatures.
"""

from __future__ import annotations

from jarvis.core.runtime import current_session
from jarvis.goals.manager import GoalManager
from jarvis.goals.models import GoalStatus
from jarvis.skills.base import BaseSkill, SkillResult

_NO_ARGS = {"type": "object", "properties": {}}
_GOAL_ID = {
    "type": "object",
    "properties": {"goal_id": {"type": "integer", "description": "The goal's id."}},
    "required": ["goal_id"],
}


class _GoalSkill(BaseSkill):
    """Base for goal tools; not fast-path matchable."""

    priority = 35

    def __init__(self, manager: GoalManager) -> None:
        self.manager = manager

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()


class AddGoalSkill(_GoalSkill):
    name = "add_goal"
    description = "Record a new goal or task the user wants to work toward."
    parameters = {
        "type": "object",
        "properties": {"goal": {"type": "string", "description": "The goal text."}},
        "required": ["goal"],
    }

    async def execute(self, goal: str = "", **_: object) -> SkillResult:
        if not goal.strip():
            return SkillResult(text="I need the goal text.")
        created = await self.manager.add(current_session(), goal)
        return SkillResult(text=f"Noted goal #{created.id}: {created.text}")


class ListGoalsSkill(_GoalSkill):
    name = "list_goals"
    description = "List the user's current open goals."
    parameters = _NO_ARGS

    async def execute(self, **_: object) -> SkillResult:
        goals = await self.manager.active(current_session())
        if not goals:
            return SkillResult(text="You have no open goals.")
        lines = [f"#{g.id}: {g.text}" for g in goals]
        return SkillResult(text="Open goals:\n" + "\n".join(lines))


def _as_goal_id(value: object) -> int | None:
    """Coerce a model-supplied goal id to int, or None if it isn't one."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class CompleteGoalSkill(_GoalSkill):
    name = "complete_goal"
    description = "Mark one of the user's goals as done, by its id."
    parameters = _GOAL_ID

    async def execute(self, goal_id: object = 0, **_: object) -> SkillResult:
        gid = _as_goal_id(goal_id)
        if gid is None:
            return SkillResult(text="Please give me a valid goal number.")
        ok = await self.manager.complete(current_session(), gid)
        return SkillResult(
            text=f"Goal #{gid} completed. Well done, Sir." if ok
            else f"I couldn't find goal #{gid}."
        )


class CancelGoalSkill(_GoalSkill):
    name = "cancel_goal"
    description = "Cancel/drop one of the user's goals, by its id."
    parameters = _GOAL_ID

    async def execute(self, goal_id: object = 0, **_: object) -> SkillResult:
        gid = _as_goal_id(goal_id)
        if gid is None:
            return SkillResult(text="Please give me a valid goal number.")
        ok = await self.manager.cancel(current_session(), gid)
        return SkillResult(
            text=f"Goal #{gid} cancelled." if ok
            else f"I couldn't find goal #{gid}."
        )


def goal_skills(manager: GoalManager) -> list[BaseSkill]:
    """Return the goal tool skills bound to ``manager``."""
    return [
        AddGoalSkill(manager),
        ListGoalsSkill(manager),
        CompleteGoalSkill(manager),
        CancelGoalSkill(manager),
    ]


# Also expose GoalStatus for callers that filter.
__all__ = ["goal_skills", "GoalStatus"]
