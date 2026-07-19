"""Goal data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class GoalStatus(str, Enum):
    """Lifecycle state of a goal."""

    ACTIVE = "active"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """A goal or task the assistant tracks for a session."""

    text: str
    id: int = 0
    session_id: str = "default"
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_open(self) -> bool:
        return self.status == GoalStatus.ACTIVE
