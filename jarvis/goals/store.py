"""Persistent goal storage (SQLite)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from jarvis.goals.models import Goal, GoalStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    text        TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goals_session ON goals(session_id);
"""


class SQLiteGoalStore:
    """Stores goals in SQLite (standard library, no external driver)."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"],
            session_id=row["session_id"],
            text=row["text"],
            status=GoalStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def add(self, goal: Goal) -> Goal:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO goals (session_id, text, status, created_at) "
                "VALUES (?, ?, ?, ?)",
                (goal.session_id, goal.text, goal.status.value,
                goal.created_at.isoformat()),
            )
            self._conn.commit()
            goal.id = int(cur.lastrowid or 0)
        return goal

    def list(self, session_id: str,
            status: GoalStatus | None = None) -> list[Goal]:
        query = "SELECT * FROM goals WHERE session_id = ?"
        params: list = [session_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY id ASC"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def set_status(self, session_id: str, goal_id: int,
                status: GoalStatus) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE goals SET status = ? WHERE id = ? AND session_id = ?",
                (status.value, goal_id, session_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM goals WHERE session_id = ?", (session_id,))
            self._conn.commit()
