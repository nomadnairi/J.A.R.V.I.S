"""
Memory subsystem (contracts).

Stage 1 defines the abstract interface only. Stage 2 will add concrete stores:
a conversation store (SQL) and a semantic long-term store (vector DB).
"""

from jarvis.memory.base import BaseMemoryStore, MemoryRecord

__all__ = ["BaseMemoryStore", "MemoryRecord"]
