"""
Abstract memory-store contract.

Defines the interface every memory backend must implement so the engine can
remember facts and recall relevant context without knowing whether the backend
is SQLite, Redis, or a vector database. Concrete implementations arrive in
Stage 2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MemoryRecord:
    """A single stored memory item."""

    content: str
    session_id: str = "default"
    kind: str = "note"          # note | fact | preference | event ...
    score: float = 0.0          # relevance score (set on recall)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class BaseMemoryStore(ABC):
    """Interface for short- and long-term memory backends."""

    @abstractmethod
    def remember(self, record: MemoryRecord) -> None:
        """Persist a memory record."""
        raise NotImplementedError

    @abstractmethod
    def recall(self, query: str, *, session_id: str = "default",
            limit: int = 5) -> list[MemoryRecord]:
        """Return records relevant to ``query``, most relevant first."""
        raise NotImplementedError

    @abstractmethod
    def forget(self, session_id: str = "default") -> None:
        """Delete stored memories (optionally scoped to a session)."""
        raise NotImplementedError
