"""Dataclasses returned by the licensing service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    """A user account."""

    id: int
    username: str
    telegram_user_id: int | None
    telegram_verified: bool
    active: bool
    created_at: float


@dataclass(frozen=True)
class License:
    """A license granted to an account (the plaintext key is shown once)."""

    id: int
    user_id: int
    plan: str
    issued_at: float
    expires_at: float | None
    revoked: bool

    def is_valid(self, *, now: float) -> bool:
        """Whether this license is currently usable."""
        if self.revoked:
            return False
        return self.expires_at is None or self.expires_at > now
