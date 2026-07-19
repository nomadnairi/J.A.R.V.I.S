"""
Goal system.

Lets J.A.R.V.I.S. track goals/tasks per session and work toward them. The LLM
can create, list, complete and cancel goals through tools, and open goals are
surfaced in its context so it stays aware of them (proactivity).
"""

from jarvis.goals.manager import GoalManager
from jarvis.goals.models import Goal, GoalStatus

__all__ = ["GoalManager", "Goal", "GoalStatus"]
