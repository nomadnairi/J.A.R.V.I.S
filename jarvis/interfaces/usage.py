"""
Per-user usage tracking for the Telegram bot (messages + tokens).

A tiny SQLite table records one row per turn so the bot can show a detailed
token report (today / this month / all time). Standard-library ``sqlite3``.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path


class UsageStore:
    """Records and aggregates per-user message/token usage."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                ts REAL NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_user ON usage(user_id, ts)")
        self._conn.commit()

    def record(self, user_id: int | str, tokens: int = 0) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO usage (user_id, tokens, ts) VALUES (?, ?, ?)",
                (str(user_id), int(tokens or 0), time.time()),
            )
            self._conn.commit()

    def stats(self, user_id: int | str, *, now: float | None = None) -> dict:
        """Return message/token totals for today, 30 days and all time."""
        now = time.time() if now is None else now
        uid = str(user_id)

        def window(since: float) -> tuple[int, int]:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(tokens), 0) AS t "
                "FROM usage WHERE user_id = ? AND ts > ?",
                (uid, since),
            ).fetchone()
            return int(row["n"]), int(row["t"])

        with self._lock:
            msgs_all, tok_all = window(0.0)
            msgs_today, tok_today = window(now - 86400)
            msgs_month, tok_month = window(now - 30 * 86400)

        return {
            "messages": msgs_all, "tokens": tok_all,
            "messages_today": msgs_today, "tokens_today": tok_today,
            "messages_month": msgs_month, "tokens_month": tok_month,
        }

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
