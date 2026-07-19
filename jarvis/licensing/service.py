"""
Account, license and login-token management backed by SQLite (standard library).

The typical lifecycle:

1. After a purchase you (the operator) run
   :meth:`LicenseService.create_account` and :meth:`LicenseService.issue_license`,
   handing the user their username, a one-time password and a license key.
2. The desktop/mobile client calls ``POST /auth/login``; the API uses
   :meth:`authenticate` then :meth:`issue_token` to return a bearer token.
3. Optionally the user links Telegram: the client asks for a pairing code
   (:meth:`create_pairing_code`), the user sends ``/link <code>`` to the bot,
   and the bot calls :meth:`confirm_pairing`.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path

from jarvis.licensing.models import Account, License

_PBKDF2_ROUNDS = 200_000
_SALT_BYTES = 16
_ALGO = "pbkdf2_sha256"


class AuthError(Exception):
    """Raised for authentication / licensing failures."""


# -- password hashing ---------------------------------------------------------

def hash_password(password: str, *, rounds: int = _PBKDF2_ROUNDS) -> str:
    """Return a ``algo$rounds$salt$hash`` string for *password*."""
    if not password:
        raise AuthError("Password must not be empty.")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"{_ALGO}${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of *password* against a stored hash."""
    try:
        algo, rounds_s, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        rounds = int(rounds_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return hmac.compare_digest(digest, expected)


def _token_hash(value: str) -> str:
    """SHA-256 hex of a token/key (only the hash is ever stored)."""
    return hashlib.sha256(value.encode()).hexdigest()


# -- service ------------------------------------------------------------------

class LicenseService:
    """SQLite-backed accounts, licenses, tokens and Telegram pairings."""

    def __init__(self, db_path: str, *, token_ttl_hours: int = 720) -> None:
        self._db_path = db_path
        self._token_ttl = token_ttl_hours * 3600
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                telegram_user_id INTEGER,
                telegram_verified INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                key_hash TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL DEFAULT 'standard',
                issued_at REAL NOT NULL,
                expires_at REAL,
                revoked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pairings (
                code TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                used INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- accounts -------------------------------------------------------------

    def create_account(self, username: str, password: str) -> Account:
        """Create an account. Raises :class:`AuthError` if the name is taken."""
        username = username.strip().lower()
        if not username:
            raise AuthError("Username must not be empty.")
        now = time.time()
        try:
            cur = self._conn.execute(
                "INSERT INTO accounts (username, password_hash, created_at) "
                "VALUES (?, ?, ?)",
                (username, hash_password(password), now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise AuthError("That username is already taken.") from exc
        return self._account_row(int(cur.lastrowid))

    def _account_from_row(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"],
            username=row["username"],
            telegram_user_id=row["telegram_user_id"],
            telegram_verified=bool(row["telegram_verified"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
        )

    def _account_row(self, user_id: int) -> Account:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise AuthError("Account not found.")
        return self._account_from_row(row)

    def get_account(self, username: str) -> Account | None:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        return self._account_from_row(row) if row else None

    def get_account_by_telegram(self, telegram_user_id: int) -> Account | None:
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE telegram_user_id = ? "
            "AND telegram_verified = 1",
            (telegram_user_id,),
        ).fetchone()
        return self._account_from_row(row) if row else None

    def set_active(self, username: str, active: bool) -> None:
        self._conn.execute(
            "UPDATE accounts SET active = ? WHERE username = ?",
            (1 if active else 0, username.strip().lower()),
        )
        self._conn.commit()

    def change_password(self, username: str, new_password: str) -> None:
        self._conn.execute(
            "UPDATE accounts SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username.strip().lower()),
        )
        self._conn.commit()

    # -- authentication -------------------------------------------------------

    def authenticate(self, username: str, password: str) -> Account:
        """Verify credentials and licensing; return the account or raise."""
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        # Always run a hash to keep timing uniform for unknown usernames.
        stored = row["password_hash"] if row else hash_password("x")
        if not verify_password(password, stored) or row is None:
            raise AuthError("Invalid username or password.")
        account = self._account_from_row(row)
        if not account.active:
            raise AuthError("This account is disabled.")
        if not self.has_active_license(account.id):
            raise AuthError("No active license for this account.")
        return account

    # -- login tokens ---------------------------------------------------------

    def issue_token(self, user_id: int) -> str:
        """Create and return a plaintext bearer token (stored hashed)."""
        token = secrets.token_urlsafe(32)
        now = time.time()
        self._conn.execute(
            "INSERT INTO tokens (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(token), user_id, now, now + self._token_ttl),
        )
        self._conn.commit()
        return token

    def validate_token(self, token: str) -> Account | None:
        """Return the account for a valid, unexpired token, else ``None``."""
        if not token:
            return None
        row = self._conn.execute(
            "SELECT a.* FROM tokens t JOIN accounts a ON a.id = t.user_id "
            "WHERE t.token_hash = ? AND t.expires_at > ? AND a.active = 1",
            (_token_hash(token), time.time()),
        ).fetchone()
        return self._account_from_row(row) if row else None

    def revoke_token(self, token: str) -> None:
        self._conn.execute(
            "DELETE FROM tokens WHERE token_hash = ?", (_token_hash(token),)
        )
        self._conn.commit()

    def purge_expired_tokens(self) -> int:
        cur = self._conn.execute(
            "DELETE FROM tokens WHERE expires_at <= ?", (time.time(),)
        )
        self._conn.commit()
        return cur.rowcount

    # -- licenses -------------------------------------------------------------

    def issue_license(
        self,
        user_id: int,
        *,
        plan: str = "standard",
        valid_days: int | None = None,
    ) -> str:
        """Grant a license and return the plaintext key (shown once)."""
        key = f"JVS-{secrets.token_urlsafe(24)}"
        now = time.time()
        expires = now + valid_days * 86400 if valid_days else None
        self._conn.execute(
            "INSERT INTO licenses (user_id, key_hash, plan, issued_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, _token_hash(key), plan, now, expires),
        )
        self._conn.commit()
        return key

    def has_active_license(self, user_id: int, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        row = self._conn.execute(
            "SELECT 1 FROM licenses WHERE user_id = ? AND revoked = 0 "
            "AND (expires_at IS NULL OR expires_at > ?) LIMIT 1",
            (user_id, now),
        ).fetchone()
        return row is not None

    def revoke_license_by_key(self, key: str) -> bool:
        cur = self._conn.execute(
            "UPDATE licenses SET revoked = 1 WHERE key_hash = ?",
            (_token_hash(key),),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_licenses(self, user_id: int) -> list[License]:
        rows = self._conn.execute(
            "SELECT * FROM licenses WHERE user_id = ? ORDER BY issued_at DESC",
            (user_id,),
        ).fetchall()
        return [
            License(
                id=r["id"],
                user_id=r["user_id"],
                plan=r["plan"],
                issued_at=r["issued_at"],
                expires_at=r["expires_at"],
                revoked=bool(r["revoked"]),
            )
            for r in rows
        ]

    # -- Telegram pairing -----------------------------------------------------

    def create_pairing_code(self, user_id: int, *, ttl_seconds: int = 600) -> str:
        """Create a short code the user sends to the bot to link Telegram."""
        code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
                    for _ in range(8))
        now = time.time()
        self._conn.execute(
            "INSERT INTO pairings (code, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (code, user_id, now, now + ttl_seconds),
        )
        self._conn.commit()
        return code

    def confirm_pairing(self, code: str, telegram_user_id: int) -> Account | None:
        """Bind *telegram_user_id* to the account for a valid pairing code."""
        code = code.strip().upper()
        row = self._conn.execute(
            "SELECT user_id FROM pairings WHERE code = ? AND used = 0 "
            "AND expires_at > ?",
            (code, time.time()),
        ).fetchone()
        if row is None:
            return None
        user_id = row["user_id"]
        with self._conn:
            self._conn.execute(
                "UPDATE pairings SET used = 1 WHERE code = ?", (code,)
            )
            self._conn.execute(
                "UPDATE accounts SET telegram_user_id = ?, telegram_verified = 1 "
                "WHERE id = ?",
                (telegram_user_id, user_id),
            )
        return self._account_row(user_id)
