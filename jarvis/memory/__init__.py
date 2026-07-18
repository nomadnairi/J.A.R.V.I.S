"""
Memory subsystem.

Provides conversation persistence and semantic (vector) recall:

    MemoryManager           — the async façade the engine uses.
    SQLiteConversationStore — persistent conversation history.
    SQLiteVectorStore       — persistent, incremental vector store (default).
    InMemoryVectorStore     — dependency-free in-memory vector store.
    HashingEmbedder         — default, offline embeddings.
    LocalEmbedder           — optional local semantic embeddings (fastembed).
    OpenAIEmbedder          — optional API-based embeddings.
    FactExtractor           — LLM-based durable-fact extraction.

All backends implement the contracts in :mod:`jarvis.memory.base`.
"""

from jarvis.memory.base import BaseEmbedder, BaseMemoryStore, MemoryRecord
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.memory.embeddings import (
    HashingEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
)
from jarvis.memory.facts import FactExtractor
from jarvis.memory.manager import MemoryManager
from jarvis.memory.sqlite_vector_store import SQLiteVectorStore
from jarvis.memory.vector_store import InMemoryVectorStore

__all__ = [
    "MemoryManager",
    "BaseMemoryStore",
    "BaseEmbedder",
    "MemoryRecord",
    "SQLiteConversationStore",
    "SQLiteVectorStore",
    "InMemoryVectorStore",
    "HashingEmbedder",
    "LocalEmbedder",
    "OpenAIEmbedder",
    "FactExtractor",
]
