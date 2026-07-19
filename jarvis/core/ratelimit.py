"""
Per-key rate limiting (token bucket).

Protects the assistant — and its API budget — from abuse when many users hit a
single instance (e.g. the Telegram bot). Each key (session id) gets its own
bucket that refills over time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    updated: float


@dataclass
class RateLimiter:
    """A token-bucket rate limiter keyed by an arbitrary string.

    ``capacity`` tokens are available per key; they refill at
    ``capacity / window_seconds`` tokens per second. Each allowed call spends
    one token.
    """

    capacity: int = 20
    window_seconds: float = 60.0
    _buckets: dict[str, _Bucket] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._refill_rate = self.capacity / self.window_seconds

    def allow(self, key: str) -> bool:
        """Consume a token for ``key``; return False if the bucket is empty."""
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _Bucket(tokens=self.capacity - 1, updated=now)
            return True
        # Refill based on elapsed time.
        elapsed = now - bucket.updated
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self._refill_rate)
        bucket.updated = now
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def remaining(self, key: str) -> float:
        bucket = self._buckets.get(key)
        return self.capacity if bucket is None else bucket.tokens
