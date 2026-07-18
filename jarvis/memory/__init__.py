"""
Memory subsystem.

Provides conversation persistence and semantic (vector) recall:

    MemoryManager           — the façade the engine uses.
    SQLiteConversationStore — persistent conversation history.
    InMemoryVectorStore     — dependency-free cosine-similarity vector store.
    HashingEmbedder         — default, offline embeddings.
    OpenAIEmbedder          — optional high-quality embeddings.

All backends implement the contracts in :mod:`jarvis.memory.base`.
"""

from jarvis.memory.base import BaseEmbedder, BaseMemoryStore, MemoryRecord
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.memory.embeddings import HashingEmbedder, OpenAIEmbedder
from jarvis.memory.manager import MemoryManager
from jarvis.memory.vector_store import InMemoryVectorStore

__all__ = [
    "MemoryManager",
    "BaseMemoryStore",
    "BaseEmbedder",
    "MemoryRecord",
    "SQLiteConversationStore",
    "InMemoryVectorStore",
    "HashingEmbedder",
    "OpenAIEmbedder",
]
