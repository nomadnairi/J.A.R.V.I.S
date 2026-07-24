"""
Session management.

Holds one :class:`~jarvis.core.context.SessionContext` per active session id,
so the engine can serve many concurrent conversations (CLI, API, voice, bot)
without leaking state between them. Sessions are LRU-evicted once the
configured cap is reached.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable

from jarvis.core.context import SessionContext
from jarvis.models.message import Conversation
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

#: A callable that loads persisted history for a session id.
HistoryLoader = Callable[[str], Conversation]


class SessionManager:
    """An LRU cache of :class:`SessionContext` objects keyed by session id.

    An optional ``loader`` populates a newly-created session's conversation
    from persistent storage (used by the memory subsystem), so a returning
    user's history is restored transparently.
    """

    def __init__(self, max_sessions: int = 1000,
                loader: HistoryLoader | None = None) -> None:
        self._sessions: "OrderedDict[str, SessionContext]" = OrderedDict()
        self._max = max_sessions
        self._loader = loader

    def get_or_create(self, session_id: str) -> SessionContext:
        """Return the context for ``session_id``, creating it if needed."""
        ctx = self._sessions.get(session_id)
        if ctx is not None:
            self._sessions.move_to_end(session_id)
            return ctx
        ctx = SessionContext(session_id=session_id)
        if self._loader is not None:
            try:
                ctx.conversation = self._loader(session_id)
            except Exception:  # noqa: BLE001 - never let loading break a session
                logger.exception("Failed to load history for session %r", session_id)
        self._sessions[session_id] = ctx
        self._evict()
        logger.debug("Created session %r (total=%d)", session_id, len(self._sessions))
        return ctx

    def get(self, session_id: str) -> SessionContext | None:
        return self._sessions.get(session_id)

    def reset(self, session_id: str) -> None:
        ctx = self._sessions.get(session_id)
        if ctx is not None:
            ctx.reset()

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _evict(self) -> None:
        while len(self._sessions) > self._max:
            evicted, _ = self._sessions.popitem(last=False)
            logger.debug("Evicted least-recently-used session %r", evicted)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._sessions)
