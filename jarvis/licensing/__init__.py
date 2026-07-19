"""Accounts, licensing and login tokens for the exe/apk clients.

The :class:`~jarvis.licensing.service.LicenseService` is a small, dependency-free
(standard-library ``sqlite3``) layer that stores user accounts, license keys,
login tokens and Telegram pairing codes. It is used by the API's auth routes.

Security notes:
    * Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-user salt.
    * License keys and login tokens are stored **hashed** (SHA-256); the plain
      value is shown to the caller once and never persisted.
    * All comparisons of secret material use constant-time ``hmac.compare_digest``.
    * Every query is parameterised.
"""

from jarvis.licensing.models import Account, License
from jarvis.licensing.service import (
    AuthError,
    LicenseService,
    hash_password,
    verify_password,
)

__all__ = [
    "Account",
    "License",
    "LicenseService",
    "AuthError",
    "hash_password",
    "verify_password",
]
