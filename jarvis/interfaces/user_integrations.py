"""
Per-user integrations with tier-gated limits.

A bot user connects their *own* integrations — a personal Home Assistant, a
custom webhook — and the number they may keep is capped by their subscription
tier (Free 2 / Plus 6 / Pro unlimited). Connections are stored per user and
validated on add, so this is a real registry, not a placeholder: adding a Home
Assistant checks the token actually works before saving.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

#: Integration kinds a user can connect themselves.
KINDS = {
    "homeassistant": "🏠 Home Assistant",
    "webhook": "🔗 Webhook",
}


def integration_limit_reached(plan, current_count: int) -> bool:
    """True if ``current_count`` is at/over what ``plan`` allows."""
    if getattr(plan, "unlimited_integrations", False):
        return False
    return current_count >= plan.integrations


@dataclass(frozen=True)
class UserIntegration:
    id: int
    kind: str
    label: str
    config: dict


class UserIntegrationsStore:
    """SQLite-backed per-user integration connections."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_integrations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                kind       TEXT NOT NULL,
                label      TEXT NOT NULL,
                config     TEXT NOT NULL,
                created_ts REAL NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_uint_user ON user_integrations(user_id)")
        self._conn.commit()

    def count(self, user_id: int | str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM user_integrations WHERE user_id = ?",
                (str(user_id),)).fetchone()
        return int(row["n"])

    def add(self, user_id: int | str, kind: str, label: str,
            config: dict) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO user_integrations (user_id, kind, label, config, "
                "created_ts) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), kind, label, json.dumps(config), time.time()))
            self._conn.commit()
            return int(cur.lastrowid)

    def list(self, user_id: int | str) -> list[UserIntegration]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM user_integrations WHERE user_id = ? ORDER BY id",
                (str(user_id),)).fetchall()
        out = []
        for r in rows:
            try:
                cfg = json.loads(r["config"])
            except json.JSONDecodeError:
                cfg = {}
            out.append(UserIntegration(r["id"], r["kind"], r["label"], cfg))
        return out

    def remove(self, integration_id: int, user_id: int | str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM user_integrations WHERE id = ? AND user_id = ?",
                (integration_id, str(user_id)))
            self._conn.commit()
            return cur.rowcount > 0

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()


async def validate(kind: str, config: dict, http=None) -> tuple[bool, str]:
    """Check a connection works before saving it. Returns (ok, detail)."""
    from jarvis.integrations.http import HttpClient
    http = http or HttpClient()
    if kind == "homeassistant":
        url = (config.get("url") or "").rstrip("/")
        token = config.get("token") or ""
        if not url or not token:
            return False, "URL and token are required."
        try:
            data = await http.get_json(
                f"{url}/api/", headers={"Authorization": f"Bearer {token}"})
        except Exception as exc:  # noqa: BLE001
            return False, f"Could not reach Home Assistant: {exc}"
        return (True, "Connected.") if isinstance(data, dict) else (False, "Bad response.")
    if kind == "webhook":
        url = config.get("url") or ""
        if not url.startswith("https://"):
            return False, "Webhook must be an https URL."
        return True, "Saved."
    return False, "Unknown integration type."
