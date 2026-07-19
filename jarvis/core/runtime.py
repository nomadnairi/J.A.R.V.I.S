"""
Per-turn runtime context.

A context variable carries the active session id through a turn so that tools
(goals, and later others) can act on the right session without threading the id
through every call signature. The engine sets it at the start of each turn;
``asyncio`` propagates context vars across ``await`` boundaries.
"""

from __future__ import annotations

from contextvars import ContextVar

_session: ContextVar[str] = ContextVar("jarvis_session", default="default")


def set_session(session_id: str) -> None:
    """Set the active session id for the current task context."""
    _session.set(session_id)


def current_session() -> str:
    """Return the active session id (``"default"`` if unset)."""
    return _session.get()
