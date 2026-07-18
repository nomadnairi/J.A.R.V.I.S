"""
Memory manager.

Ties the pieces of the memory subsystem together and exposes the small surface
the engine needs:

* **persistence** — every turn is written to the conversation store, so history
  survives restarts, and sessions can be reloaded on demand;
* **semantic recall** — meaningful exchanges are embedded into the vector store
  and relevant ones are recalled to enrich the LLM's context (RAG).
"""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.memory.base import BaseEmbedder, BaseMemoryStore, MemoryRecord
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.memory.embeddings import HashingEmbedder, OpenAIEmbedder
from jarvis.memory.vector_store import InMemoryVectorStore
from jarvis.models.message import Conversation, Message
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Coordinates conversation persistence and semantic recall."""

    def __init__(
        self,
        vector_store: BaseMemoryStore,
        conversation_store: SQLiteConversationStore,
        *,
        recall_limit: int = 4,
    ) -> None:
        self.vectors = vector_store
        self.conversations = conversation_store
        self.recall_limit = recall_limit

    # -- construction -------------------------------------------------------

    @classmethod
    def from_settings(cls, settings: Settings) -> "MemoryManager":
        embedder = cls._make_embedder(settings)
        vector_store = cls._make_vector_store(settings, embedder)
        conversation_store = SQLiteConversationStore(settings.memory_db_path)
        return cls(
            vector_store,
            conversation_store,
            recall_limit=settings.memory_recall_limit,
        )

    @staticmethod
    def _make_embedder(settings: Settings) -> BaseEmbedder:
        if settings.embedding_backend == "openai" and settings.openai_api_key:
            return OpenAIEmbedder(settings.openai_api_key)
        return HashingEmbedder()

    @staticmethod
    def _make_vector_store(settings: Settings, embedder: BaseEmbedder) -> BaseMemoryStore:
        if settings.memory_backend == "chroma":
            from jarvis.memory.chroma_store import ChromaVectorStore
            return ChromaVectorStore(embedder, path=settings.vector_store_path)
        return InMemoryVectorStore(
            embedder=embedder, persist_path=settings.memory_vector_path
        )

    # -- persistence --------------------------------------------------------

    #: How many recent messages to reload into a session's live context.
    history_limit: int = 50

    def load_conversation(self, session_id: str) -> Conversation:
        """Load recent persisted history for a session."""
        return self.conversations.load(session_id, limit=self.history_limit)

    def persist_message(self, session_id: str, message: Message) -> None:
        self.conversations.append(session_id, message)

    def persist_turn(self, session_id: str, user: str, assistant: str) -> None:
        """Persist a full turn (user + assistant) to the conversation store."""
        self.conversations.append_exchange(session_id, user, assistant)

    # -- semantic memory ----------------------------------------------------

    def remember(self, session_id: str, content: str, *, kind: str = "exchange",
                metadata: dict | None = None) -> None:
        """Store ``content`` in the semantic vector store."""
        self.vectors.remember(
            MemoryRecord(content=content, session_id=session_id, kind=kind,
                        metadata=metadata or {})
        )

    def recall(self, query: str, *, session_id: str = "default",
            limit: int | None = None) -> list[MemoryRecord]:
        return self.vectors.recall(
            query, session_id=session_id, limit=limit or self.recall_limit
        )

    def recall_context(self, query: str, *, session_id: str = "default") -> str | None:
        """Return recalled memories formatted for system-prompt injection."""
        records = self.recall(query, session_id=session_id)
        if not records:
            return None
        lines = ["Relevant things you remember from earlier:"]
        lines.extend(f"- {r.content}" for r in records)
        return "\n".join(lines)

    # -- lifecycle ----------------------------------------------------------

    def forget(self, session_id: str | None = "default") -> None:
        """Clear both semantic memory and stored history for a session."""
        self.vectors.forget(session_id)
        self.conversations.clear(session_id)

    def stats(self) -> dict:
        return {
            "memories": self.vectors.count(),
            "stored_messages": self.conversations.count(),
            "sessions": len(self.conversations.sessions()),
        }
