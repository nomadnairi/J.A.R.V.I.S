"""
Per-user preferences (SQLite).

Stores small, durable per-user settings — currently the preferred language —
for interfaces like the Telegram bot. Uses the standard-library ``sqlite3``;
no external dependency.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_prefs (
    user_id   TEXT PRIMARY KEY,
    language  TEXT
);
"""


class UserPreferences:
    """A tiny SQLite-backed key store for per-user settings."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        # Add columns to databases created before they existed.
        columns = {row["name"] for row in
                self._conn.execute("PRAGMA table_info(user_prefs)")}
        if "model_profile" not in columns:
            self._conn.execute(
                "ALTER TABLE user_prefs ADD COLUMN model_profile TEXT")
        if "model_id" not in columns:
            self._conn.execute(
                "ALTER TABLE user_prefs ADD COLUMN model_id TEXT")
        self._conn.commit()

    def get_language(self, user_id: int | str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT language FROM user_prefs WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
        return row["language"] if row else None

    def set_language(self, user_id: int | str, language: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, language) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET language = excluded.language",
                (str(user_id), language),
            )
            self._conn.commit()

    def get_model(self, user_id: int | str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT model_profile FROM user_prefs WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
        return row["model_profile"] if row and row["model_profile"] else None

    def set_model(self, user_id: int | str, profile: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, model_profile) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "model_profile = excluded.model_profile",
                (str(user_id), profile),
            )
            self._conn.commit()

    def get_model_id(self, user_id: int | str) -> str | None:
        """The user's specific chosen model (OpenRouter slug), if any."""
        with self._lock:
            row = self._conn.execute(
                "SELECT model_id FROM user_prefs WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
        return row["model_id"] if row and row["model_id"] else None

    def set_model_id(self, user_id: int | str, model_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, model_id) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET model_id = excluded.model_id",
                (str(user_id), model_id),
            )
            self._conn.commit()

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
