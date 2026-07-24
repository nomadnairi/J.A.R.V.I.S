"""
Task automation — recurring tasks the assistant runs on a schedule.

Users type "каждый день в 9:00 сделай сводку новостей" / "every monday at 18:00
…" / "каждые 3 часа проверь почту" and a background worker runs the task through
the engine at each due time and delivers the result. Unlike a one-shot reminder,
an automation reschedules itself after every run.

The parser + next-run maths are pure and unit-tested; the store is SQLite.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_TRIGGERS = ("каждый", "каждую", "каждые", "every")

_WEEKDAYS = {
    "понедельник": 0, "пн": 0, "monday": 0, "mon": 0,
    "вторник": 1, "вт": 1, "tuesday": 1, "tue": 1,
    "среда": 2, "среду": 2, "ср": 2, "wednesday": 2, "wed": 2,
    "четверг": 3, "чт": 3, "thursday": 3, "thu": 3,
    "пятница": 4, "пятницу": 4, "пт": 4, "friday": 4, "fri": 4,
    "суббота": 5, "субботу": 5, "сб": 5, "saturday": 5, "sat": 5,
    "воскресенье": 6, "вс": 6, "sunday": 6, "sun": 6,
}

# "каждые N часов/минут"
_INTERVAL = re.compile(
    r"кажд\w*\s+(\d+)\s*(час\w*|hour\w*|h|мин\w*|min\w*)\b", re.IGNORECASE)
# "every N hours/minutes"
_INTERVAL_EN = re.compile(
    r"every\s+(\d+)\s*(hour\w*|h|min\w*)\b", re.IGNORECASE)
# a time of day "в 9:00" / "at 18:30" / "в 9"
_AT = re.compile(r"(?:в|at)\s*(\d{1,2})(?:[:.](\d{2}))?\b", re.IGNORECASE)


@dataclass(frozen=True)
class Automation:
    """A recurring task specification."""

    kind: str            # "daily" | "weekly" | "interval"
    prompt: str
    hour: int = 9
    minute: int = 0
    weekday: int = 0     # for weekly (0 = Monday)
    interval: int = 0    # seconds, for interval


def is_automation(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(_TRIGGERS)


def parse_automation(text: str, now: datetime) -> Automation | None:
    """Parse a recurring-task request, or ``None`` if it isn't one."""
    raw = text.strip()
    if not is_automation(raw):
        return None
    low = raw.lower()

    # 1) Interval: "каждые 3 часа …" / "every 30 minutes …"
    m = _INTERVAL.search(low) or _INTERVAL_EN.search(low)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        secs = n * 60 if unit.startswith(("мин", "min")) else n * 3600
        if secs <= 0:
            return None
        body = _strip(raw, m.end())
        return Automation(kind="interval", prompt=body, interval=secs)

    # A time of day is required for daily/weekly.
    tm = _AT.search(low)
    hour = int(tm.group(1)) if tm else 9
    minute = int(tm.group(2) or 0) if tm else 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    # 2) Weekly: "каждый понедельник в 18:00 …"
    for word, wd in _WEEKDAYS.items():
        if re.search(rf"\b{word}\b", low):
            body = _strip(raw, tm.end() if tm else 0, word)
            return Automation(kind="weekly", prompt=body, hour=hour,
                            minute=minute, weekday=wd)

    # 3) Daily: "каждый день в 9:00 …" / "every day at 9 …"
    if re.search(r"\b(день|day)\b", low) or tm:
        body = _strip(raw, tm.end() if tm else 0)
        return Automation(kind="daily", prompt=body, hour=hour, minute=minute)
    return None


def _strip(raw: str, after: int, word: str = "") -> str:
    """Best-effort extraction of the task body from the request."""
    body = raw[after:] if after else raw
    # Drop leading trigger + schedule words that may remain.
    for junk in (*_TRIGGERS, "день", "day", word):
        if junk:
            body = re.sub(rf"^\s*{re.escape(junk)}\b", "", body,
                        flags=re.IGNORECASE).strip(" ,:—-")
    return body.strip(" ,:—-")


def next_run(spec: Automation, now: datetime) -> float:
    """Timestamp of the next time this automation should fire."""
    if spec.kind == "interval":
        return (now + timedelta(seconds=spec.interval)).timestamp()
    base = now.replace(hour=spec.hour, minute=spec.minute,
                    second=0, microsecond=0)
    if spec.kind == "weekly":
        days = (spec.weekday - now.weekday()) % 7
        cand = base + timedelta(days=days)
        if cand <= now:
            cand += timedelta(days=7)
        return cand.timestamp()
    # daily
    if base <= now:
        base += timedelta(days=1)
    return base.timestamp()


class AutomationStore:
    """SQLite-backed recurring automations."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS automations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                chat_id     TEXT NOT NULL,
                prompt      TEXT NOT NULL,
                kind        TEXT NOT NULL,
                hour        INTEGER NOT NULL DEFAULT 9,
                minute      INTEGER NOT NULL DEFAULT 0,
                weekday     INTEGER NOT NULL DEFAULT 0,
                interval    INTEGER NOT NULL DEFAULT 0,
                next_ts     REAL NOT NULL,
                enabled     INTEGER NOT NULL DEFAULT 1,
                created_ts  REAL NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_auto_due ON automations(enabled, next_ts)")
        self._conn.commit()

    def add(self, user_id: int | str, chat_id: int | str,
            spec: Automation, next_ts: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO automations (user_id, chat_id, prompt, kind, hour, "
                "minute, weekday, interval, next_ts, created_ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(user_id), str(chat_id), spec.prompt, spec.kind, spec.hour,
                spec.minute, spec.weekday, spec.interval, float(next_ts),
                time.time()))
            self._conn.commit()
            return int(cur.lastrowid)

    def due(self, now: float | None = None) -> list[sqlite3.Row]:
        now = time.time() if now is None else now
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM automations WHERE enabled = 1 AND next_ts <= ? "
                "ORDER BY next_ts", (now,)))

    def reschedule(self, automation_id: int, next_ts: float) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE automations SET next_ts = ? WHERE id = ?",
                (float(next_ts), automation_id))
            self._conn.commit()

    def list_active(self, user_id: int | str,
                    limit: int = 10) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(
                "SELECT * FROM automations WHERE user_id = ? AND enabled = 1 "
                "ORDER BY next_ts LIMIT ?", (str(user_id), limit)))

    def cancel(self, automation_id: int, user_id: int | str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE automations SET enabled = 0 WHERE id = ? AND user_id = ? "
                "AND enabled = 1", (automation_id, str(user_id)))
            self._conn.commit()
            return cur.rowcount > 0

    def spec_of(self, row: sqlite3.Row) -> Automation:
        return Automation(kind=row["kind"], prompt=row["prompt"],
                        hour=row["hour"], minute=row["minute"],
                        weekday=row["weekday"], interval=row["interval"])

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
