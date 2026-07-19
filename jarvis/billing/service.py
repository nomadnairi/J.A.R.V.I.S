"""
Turn confirmed payments into accounts + licenses (idempotently).

The service is deliberately small: it does NOT talk to payment providers.
Something upstream (the Telegram bot's payment handler, or your payment
processor's webhook relay) confirms that money arrived and calls
:meth:`BillingService.process_payment` with a unique charge id. The charge id
is the idempotency key — processing the same charge twice returns ``None``
instead of issuing another license.
"""

from __future__ import annotations

import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from jarvis.licensing import AuthError, LicenseService
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Fulfillment:
    """What a processed payment produced."""

    username: str
    #: One-time password — only set when the account was just created.
    password: str | None
    license_key: str
    plan: str
    created_account: bool


class BillingService:
    """Records payments and provisions accounts/licenses."""

    def __init__(self, licenses: LicenseService, db_path: str) -> None:
        self._licenses = licenses
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                charge_id TEXT PRIMARY KEY,
                telegram_user_id INTEGER,
                username TEXT,
                plan TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- core -------------------------------------------------------------

    def already_processed(self, charge_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM payments WHERE charge_id = ?", (charge_id,)
        ).fetchone()
        return row is not None

    def process_payment(
        self,
        charge_id: str,
        *,
        telegram_user_id: int | None = None,
        username: str | None = None,
        plan: str = "standard",
        valid_days: int | None = None,
    ) -> Fulfillment | None:
        """Provision for a confirmed payment; ``None`` if already processed.

        Account resolution order: an account already linked to
        *telegram_user_id* → an existing account named *username* → a brand
        new account (with a generated one-time password).
        """
        charge_id = (charge_id or "").strip()
        if not charge_id:
            raise AuthError("A charge id is required.")
        if self.already_processed(charge_id):
            logger.info("Duplicate payment %s ignored.", charge_id)
            return None

        account = None
        password: str | None = None
        created = False
        if telegram_user_id is not None:
            account = self._licenses.get_account_by_telegram(telegram_user_id)
        if account is None and username:
            account = self._licenses.get_account(username)
        if account is None:
            name = self._unique_username(
                username or (f"user{telegram_user_id}" if telegram_user_id
                            else f"user{secrets.token_hex(4)}")
            )
            password = secrets.token_urlsafe(9)
            account = self._licenses.create_account(name, password)
            created = True
            if telegram_user_id is not None:
                # The buyer paid from this Telegram account — link it.
                code = self._licenses.create_pairing_code(account.id)
                self._licenses.confirm_pairing(code, telegram_user_id)

        key = self._licenses.issue_license(
            account.id, plan=plan, valid_days=valid_days
        )
        self._conn.execute(
            "INSERT INTO payments (charge_id, telegram_user_id, username, plan, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (charge_id, telegram_user_id, account.username, plan, time.time()),
        )
        self._conn.commit()
        logger.info("Payment %s fulfilled for %s (plan=%s, new=%s).",
                    charge_id, account.username, plan, created)
        return Fulfillment(
            username=account.username,
            password=password,
            license_key=key,
            plan=plan,
            created_account=created,
        )

    # -- overview / admin ------------------------------------------------

    def stats(self) -> dict:
        """Payment counters for the admin panel."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM payments").fetchone()[0]
        last30 = self._conn.execute(
            "SELECT COUNT(*) FROM payments WHERE created_at > ?",
            (time.time() - 30 * 86400,),
        ).fetchone()[0]
        return {"payments": total or 0, "payments_30d": last30 or 0}

    def recent_payments(self, limit: int = 10) -> list[dict]:
        """Most recent payments, newest first."""
        rows = self._conn.execute(
            "SELECT charge_id, telegram_user_id, username, plan, created_at "
            "FROM payments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _unique_username(self, base: str) -> str:
        base = base.strip().lower() or "user"
        candidate = base
        suffix = 1
        while self._licenses.get_account(candidate) is not None:
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate
