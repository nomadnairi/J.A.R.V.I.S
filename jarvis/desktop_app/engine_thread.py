"""
Run the async :class:`~jarvis.core.engine.JarvisEngine` behind a synchronous
facade.

The GUI thread must never block on the LLM, and the engine is asyncio-based —
so a dedicated thread owns an event loop and the engine, and the GUI submits
work with :meth:`ask` (blocking, for worker threads) or :meth:`ask_async`
(callback-based, for signal/slot wiring).
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Callable

from jarvis.config.settings import Settings
from jarvis.core.engine import JarvisEngine


class EngineThread:
    """Owns an event loop + engine on a background thread."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._loop: asyncio.AbstractEventLoop | None = None
        self._engine: JarvisEngine | None = None
        self._started = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="jarvis-engine")

    # -- lifecycle ------------------------------------------------------------

    def start(self, timeout: float = 30.0) -> None:
        self._thread.start()
        if not self._started.wait(timeout):
            raise RuntimeError("Engine thread failed to start in time.")

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._engine = JarvisEngine(self._settings)
        self._loop.run_until_complete(self._engine.start())
        self._started.set()
        self._loop.run_forever()
        # Drain: shut the engine down inside the loop before closing it.
        self._loop.run_until_complete(self._engine.shutdown())
        self._loop.close()

    def stop(self, timeout: float = 10.0) -> None:
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout)

    @property
    def engine(self) -> JarvisEngine:
        if self._engine is None:
            raise RuntimeError("Engine thread is not started.")
        return self._engine

    # -- calls ------------------------------------------------------------

    def submit(self, coro) -> Future:
        """Schedule a coroutine on the engine loop; returns a Future."""
        if self._loop is None:
            raise RuntimeError("Engine thread is not started.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def ask(self, text: str, *, session_id: str = "desktop",
            timeout: float = 300.0) -> str:
        """Blocking ask — call from a worker thread, never the GUI thread."""
        return self.submit(
            self.engine.ask(text, session_id=session_id)
        ).result(timeout)

    def ask_async(self, text: str, *, session_id: str = "desktop",
                on_done: Callable[[str | None, Exception | None], None]) -> None:
        """Non-blocking ask; ``on_done(reply, error)`` fires on completion.

        The callback runs on the engine thread — GUI code should marshal it
        back to the UI thread (e.g. via a Qt signal).
        """
        future = self.submit(self.engine.ask(text, session_id=session_id))

        def _done(fut: Future) -> None:
            try:
                on_done(fut.result(), None)
            except Exception as exc:  # noqa: BLE001 - surfaced to the UI
                on_done(None, exc)

        future.add_done_callback(_done)

    def stream_async(self, text: str, *, session_id: str = "desktop",
                    on_chunk: Callable[[str], None],
                    on_done: Callable[[Exception | None], None]) -> None:
        """Stream a reply; ``on_chunk`` fires per chunk, ``on_done`` at the end.

        Both callbacks run on the engine thread — marshal to the UI thread.
        """
        from jarvis.models.response import Request

        async def _consume() -> None:
            async for chunk in self.engine.stream(
                Request(text=text, session_id=session_id)
            ):
                on_chunk(chunk)

        future = self.submit(_consume())

        def _done(fut: Future) -> None:
            try:
                fut.result()
                on_done(None)
            except Exception as exc:  # noqa: BLE001 - surfaced to the UI
                on_done(exc)

        future.add_done_callback(_done)

    def reset(self, session_id: str = "desktop") -> None:
        self.submit(self.engine.reset(session_id)).result(30)

    def forget(self, session_id: str = "desktop") -> None:
        self.submit(self.engine.forget(session_id)).result(30)
