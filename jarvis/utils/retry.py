"""
Retry helpers with exponential backoff.

Used by the LLM client (and later by integrations) to survive transient
network / rate-limit failures without hand-rolling retry loops everywhere.
"""

from __future__ import annotations

import functools
import random
import time
from typing import Callable, TypeVar

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry(
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a callable with exponential backoff.

    Args:
        attempts: Total number of tries (including the first).
        base_delay: Delay before the first retry, in seconds.
        max_delay: Upper bound on any single delay.
        backoff: Multiplier applied to the delay after each failure.
        jitter: Add random jitter to avoid thundering-herd retries.
        exceptions: Exception types that should trigger a retry.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt == attempts:
                        break
                    sleep_for = min(delay, max_delay)
                    if jitter:
                        sleep_for += random.uniform(0, sleep_for * 0.1)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    delay *= backoff
            assert last_exc is not None  # for type checkers
            raise last_exc

        return wrapper

    return decorator
