"""
Retry helpers with exponential backoff.

Used by the LLM client (and later by integrations) to survive transient
network / rate-limit failures without hand-rolling retry loops everywhere.
Both synchronous (:func:`retry`) and asynchronous (:func:`retry_async`)
variants are provided.
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Awaitable, Callable, TypeVar

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def _next_delay(delay: float, max_delay: float, jitter: bool) -> float:
    sleep_for = min(delay, max_delay)
    if jitter:
        # Non-security: retry jitter only, no cryptographic requirement.
        sleep_for += random.uniform(0, sleep_for * 0.1)  # noqa: S311  # nosec B311
    return sleep_for


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
                    sleep_for = _next_delay(delay, max_delay, jitter)
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


def retry_async(
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Async counterpart of :func:`retry` using :func:`asyncio.sleep`."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt == attempts:
                        break
                    sleep_for = _next_delay(delay, max_delay, jitter)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        sleep_for,
                    )
                    await asyncio.sleep(sleep_for)
                    delay *= backoff
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
