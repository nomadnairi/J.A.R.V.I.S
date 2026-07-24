"""
Reminders + a tiny natural-time parser for the Telegram bot.

Users type "напомни через 10 минут купить хлеб" / "remind me tomorrow at 9 call
mom" and the bot stores a reminder that a background worker fires at the due
time. The parser handles the common Russian/English forms; anything it can't
parse returns ``None`` and the bot shows a short hint.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Trigger words that start a reminder request.
_TRIGGERS = ("напомни мне", "напомни", "remind me", "remind", "eslat")

# "через N единиц"
_REL = re.compile(
    r"(?:через|in)\s+(\d+)\s*"
    r"(мин|минут\w*|min\w*|час\w*|hour\w*|h|дн\w*|день|day\w*|d)\b",
    re.IGNORECASE)
# "завтра/послезавтра/сегодня [в] HH[:MM]" or just "в HH[:MM]"
_AT = re.compile(
    r"\b(послезавтра|завтра|сегодня|tomorrow|today)?\s*"
    r"(?:в|at)?\s*(\d{1,2})(?:[:.](\d{2}))?\b",
    re.IGNORECASE)

_MIN = {"min", "мин"}
_HOUR = {"h", "hour", "час"}
_DAY = {"d", "day", "дн", "день"}


def _unit_kind(unit: str) -> str:
    u = unit.lower()
    if u.startswith(("мин", "min")):
        return "min"
    if u.startswith(("час", "hour")) or u == "h":
        return "hour"
    return "day"


def _strip_trigger(text: str) -> str | None:
    low = text.strip().lower()
    for trig in _TRIGGERS:
        if low.startswith(trig):
            return text.strip()[len(trig):].strip(" ,:—-")
    return None


def is_reminder(text: str) -> bool:
    """Whether ``text`` starts with a reminder trigger word."""
    return _strip_trigger(text) is not None


def parse_reminder(text: str, now: datetime) -> tuple[datetime, str] | None:
    """Parse a reminder request into ``(due_datetime, body)`` or ``None``."""
    rest = _strip_trigger(text)
    if rest is None:
        return None

    # 1) Relative: "через 10 минут …"
    m = _REL.search(rest)
    if m:
        amount, kind = int(m.group(1)), _unit_kind(m.group(2))
        delta = {"min": timedelta(minutes=amount),
                "hour": timedelta(hours=amount),
                "day": timedelta(days=amount)}[kind]
        body = (rest[:m.start()] + " " + rest[m.end():]).strip(" ,:—-")
        return now + delta, body or ""

    # 2) Absolute time of day: "завтра в 18:00 …", "в 9 …"
    m = _AT.search(rest)
    if m and (m.group(2) is not None):
        hour = int(m.group(2))
        minute = int(m.group(3) or 0)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        day_word = (m.group(1) or "").lower()
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day_word in ("завтра", "tomorrow"):
            due += timedelta(days=1)
        elif day_word == "послезавтра":
            due += timedelta(days=2)
        elif due <= now:  # today's time already passed → tomorrow
            due += timedelta(days=1)
        body = (rest[:m.start()] + " " + rest[m.end():]).strip(" ,:—-")
        return due, body or ""

    return None


class ReminderStore:
    """SQLite-backed reminders with a due-query for the worker."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                chat_id    TEXT NOT NULL,
                text       TEXT NOT NULL,
                due_ts     REAL NOT NULL,
                created_ts REAL NOT NULL,
                fired      INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rem_due ON reminders(fired, due_ts)")
        self._conn.commit()

    def add(self, user_id: int | str, chat_id: int | str, text: str,
            due_ts: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO reminders (user_id, chat_id, text, due_ts, "
                "created_ts) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), str(chat_id), text, float(due_ts), time.time()))
            self._conn.commit()
            return int(cur.lastrowid)

    def due(self, now: float | None = None) -> list[sqlite3.Row]:
        now = time.time() if now is None else now
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM reminders WHERE fired = 0 AND due_ts <= ? "
                "ORDER BY due_ts", (now,)))

    def mark_fired(self, reminder_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))
            self._conn.commit()

    def list_active(self, user_id: int | str, now: float | None = None,
                    limit: int = 10) -> list[sqlite3.Row]:
        now = time.time() if now is None else now
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM reminders WHERE user_id = ? AND fired = 0 AND "
                "due_ts > ? ORDER BY due_ts LIMIT ?",
                (str(user_id), now, limit)))

    def cancel(self, reminder_id: int, user_id: int | str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE reminders SET fired = 1 WHERE id = ? AND user_id = ? "
                "AND fired = 0", (reminder_id, str(user_id)))
            self._conn.commit()
            return cur.rowcount > 0

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
