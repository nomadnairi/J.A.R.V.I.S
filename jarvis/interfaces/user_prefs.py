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
        # Bring-your-own-key + a per-user assistant name (white-label).
        for col in ("byok_provider", "byok_key", "byok_model", "chat_id",
                    "assistant_name"):
            if col not in columns:
                self._conn.execute(
                    f"ALTER TABLE user_prefs ADD COLUMN {col} TEXT")
        # Proactive messaging opt-in + last-seen timestamp.
        if "proactive" not in columns:
            self._conn.execute(
                "ALTER TABLE user_prefs ADD COLUMN proactive INTEGER DEFAULT 0")
        if "last_seen" not in columns:
            self._conn.execute(
                "ALTER TABLE user_prefs ADD COLUMN last_seen REAL DEFAULT 0")
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

    def get_assistant_name(self, user_id: int | str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT assistant_name FROM user_prefs WHERE user_id = ?",
                (str(user_id),)).fetchone()
        return row["assistant_name"] if row and row["assistant_name"] else None

    def set_assistant_name(self, user_id: int | str, name: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, assistant_name) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "assistant_name = excluded.assistant_name",
                (str(user_id), name))
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

    def get_byok(self, user_id: int | str) -> dict | None:
        """The user's own provider credentials, or ``None`` if not connected."""
        with self._lock:
            row = self._conn.execute(
                "SELECT byok_provider, byok_key, byok_model FROM user_prefs "
                "WHERE user_id = ?", (str(user_id),),
            ).fetchone()
        if not row or not row["byok_provider"] or not row["byok_key"]:
            return None
        return {"provider": row["byok_provider"], "key": row["byok_key"],
                "model": row["byok_model"] or ""}

    def set_byok(self, user_id: int | str, provider: str, key: str,
                model: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, byok_provider, byok_key, "
                "byok_model) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE "
                "SET byok_provider = excluded.byok_provider, "
                "byok_key = excluded.byok_key, byok_model = excluded.byok_model",
                (str(user_id), provider, key, model),
            )
            self._conn.commit()

    def clear_byok(self, user_id: int | str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE user_prefs SET byok_provider = NULL, byok_key = NULL, "
                "byok_model = NULL WHERE user_id = ?", (str(user_id),),
            )
            self._conn.commit()

    def touch(self, user_id: int | str, chat_id: int | str) -> None:
        """Record the user's chat id and last-seen time (for proactive msgs)."""
        import time as _time
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, chat_id, last_seen) "
                "VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                "chat_id = excluded.chat_id, last_seen = excluded.last_seen",
                (str(user_id), str(chat_id), _time.time()))
            self._conn.commit()

    def get_proactive(self, user_id: int | str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT proactive FROM user_prefs WHERE user_id = ?",
                (str(user_id),)).fetchone()
        return bool(row["proactive"]) if row else False

    def set_proactive(self, user_id: int | str, on: bool) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_prefs (user_id, proactive) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET proactive = excluded.proactive",
                (str(user_id), 1 if on else 0))
            self._conn.commit()

    def list_proactive(self) -> list:
        """Rows (user_id, chat_id, last_seen, language) for opted-in users."""
        with self._lock:
            return list(self._conn.execute(
                "SELECT user_id, chat_id, last_seen, language FROM user_prefs "
                "WHERE proactive = 1 AND chat_id IS NOT NULL"))

    def get_chat_id(self, user_id: int | str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT chat_id FROM user_prefs WHERE user_id = ?",
                (str(user_id),)).fetchone()
        return row["chat_id"] if row and row["chat_id"] else None

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
