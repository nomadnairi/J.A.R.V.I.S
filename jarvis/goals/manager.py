"""Async goal manager — the facade the engine and tools use."""

from __future__ import annotations

import asyncio

from jarvis.config.settings import Settings
from jarvis.goals.models import Goal, GoalStatus
from jarvis.goals.store import SQLiteGoalStore


class GoalManager:
    """Coordinates goal persistence; blocking I/O runs off the event loop."""

    def __init__(self, store: SQLiteGoalStore) -> None:
        self.store = store

    @classmethod
    def from_settings(cls, settings: Settings) -> "GoalManager":
        return cls(SQLiteGoalStore(settings.memory_db_path))

    async def add(self, session_id: str, text: str) -> Goal:
        return await asyncio.to_thread(
            self.store.add, Goal(text=text.strip(), session_id=session_id)
        )

    async def list(self, session_id: str,
                status: GoalStatus | None = None) -> list[Goal]:
        return await asyncio.to_thread(self.store.list, session_id, status)

    async def active(self, session_id: str) -> list[Goal]:
        return await self.list(session_id, GoalStatus.ACTIVE)

    async def complete(self, session_id: str, goal_id: int) -> bool:
        return await asyncio.to_thread(
            self.store.set_status, session_id, goal_id, GoalStatus.DONE
        )

    async def cancel(self, session_id: str, goal_id: int) -> bool:
        return await asyncio.to_thread(
            self.store.set_status, session_id, goal_id, GoalStatus.CANCELLED
        )

    async def clear(self, session_id: str) -> None:
        await asyncio.to_thread(self.store.clear, session_id)
