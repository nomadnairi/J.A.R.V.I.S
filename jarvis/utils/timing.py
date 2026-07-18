"""
Lightweight timing helpers.

A context manager and decorator for measuring wall-clock duration, used to
feed latency numbers into the telemetry layer.
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")


class Stopwatch:
    """A simple monotonic stopwatch.

    Example:
        sw = Stopwatch().start()
        ... work ...
        elapsed_ms = sw.stop()
    """

    def __init__(self) -> None:
        self._start: float | None = None
        self.elapsed_ms: float = 0.0

    def start(self) -> "Stopwatch":
        self._start = time.perf_counter()
        return self

    def stop(self) -> float:
        if self._start is None:
            raise RuntimeError("Stopwatch.stop() called before start().")
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        return self.elapsed_ms


@contextmanager
def measure() -> Iterator[Stopwatch]:
    """Context manager yielding a :class:`Stopwatch`.

    Example:
        with measure() as sw:
            do_work()
        print(sw.elapsed_ms)
    """
    sw = Stopwatch().start()
    try:
        yield sw
    finally:
        sw.stop()


def timed(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that attaches ``last_call_ms`` to the wrapped function."""

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        with measure() as sw:
            result = func(*args, **kwargs)
        wrapper.last_call_ms = sw.elapsed_ms  # type: ignore[attr-defined]
        return result

    wrapper.last_call_ms = 0.0  # type: ignore[attr-defined]
    return wrapper
