"""
Referral tracking for the Telegram bot (SQLite).

Each user gets an invite link (``?start=ref_<id>``). When a new user starts the
bot through it, we record the referral once (a user can only ever be referred by
one person, and never by themselves). The referrer earns a bonus to their daily
message allowance, proportional to how many people they've brought in.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path


class ReferralStore:
    """Records who referred whom and counts a user's referrals."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                referred_id  TEXT PRIMARY KEY,
                referrer_id  TEXT NOT NULL,
                ts           REAL NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ref_referrer "
            "ON referrals(referrer_id)")
        self._conn.commit()

    def record(self, referrer_id: int | str, referred_id: int | str) -> bool:
        """Record that ``referred_id`` joined via ``referrer_id``.

        Returns ``True`` if this is a new, valid referral; ``False`` if the user
        was already referred, referred themselves, or the ids are invalid.
        """
        referrer, referred = str(referrer_id), str(referred_id)
        if not referrer or not referred or referrer == referred:
            return False
        with self._lock:
            if self._conn.execute(
                "SELECT 1 FROM referrals WHERE referred_id = ?", (referred,)
            ).fetchone():
                return False
            self._conn.execute(
                "INSERT INTO referrals (referred_id, referrer_id, ts) "
                "VALUES (?, ?, ?)", (referred, referrer, time.time()))
            self._conn.commit()
        return True

    def count(self, referrer_id: int | str) -> int:
        """How many users ``referrer_id`` has brought in."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM referrals WHERE referrer_id = ?",
                (str(referrer_id),),
            ).fetchone()
        return int(row["n"]) if row else 0

    def referred_by(self, referred_id: int | str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT referrer_id FROM referrals WHERE referred_id = ?",
                (str(referred_id),),
            ).fetchone()
        return row["referrer_id"] if row else None

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
