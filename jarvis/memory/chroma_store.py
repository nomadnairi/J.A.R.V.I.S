"""
Optional ChromaDB-backed vector store.

Implements the same :class:`BaseMemoryStore` contract as
:class:`~jarvis.memory.vector_store.InMemoryVectorStore`, so it is a drop-in
replacement for larger, persistent deployments. ChromaDB is imported lazily;
the dependency is only needed if this backend is selected.
"""

from __future__ import annotations

import uuid

from jarvis.memory.base import BaseEmbedder, BaseMemoryStore, MemoryRecord
from jarvis.utils.exceptions import MemoryError as JarvisMemoryError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore(BaseMemoryStore):
    """A :class:`BaseMemoryStore` backed by ChromaDB."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        path: str = "chroma_db",
        collection: str = "jarvis_memory",
    ) -> None:
        self.embedder = embedder
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise JarvisMemoryError(
                "ChromaVectorStore requires the 'chromadb' package. "
                "Install it or use the default in-memory backend."
            ) from exc
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(collection)

    def remember(self, record: MemoryRecord) -> None:
        embedding = self.embedder.embed(record.content)
        self._collection.add(
            ids=[uuid.uuid4().hex],
            embeddings=[embedding],
            documents=[record.content],
            metadatas=[{
                "session_id": record.session_id,
                "kind": record.kind,
                "timestamp": record.timestamp.isoformat(),
            }],
        )

    def recall(self, query: str, *, session_id: str | None = "default",
            limit: int = 5) -> list[MemoryRecord]:
        where = {"session_id": session_id} if session_id is not None else None
        result = self._collection.query(
            query_embeddings=[self.embedder.embed(query)],
            n_results=limit,
            where=where,
        )
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        records: list[MemoryRecord] = []
        for doc, meta, dist in zip(docs, metas, distances):
            records.append(
                MemoryRecord(
                    content=doc,
                    session_id=(meta or {}).get("session_id", "default"),
                    kind=(meta or {}).get("kind", "note"),
                    score=1.0 - float(dist),  # distance -> similarity
                )
            )
        return records

    def forget(self, session_id: str | None = "default") -> None:
        if session_id is None:
            # Recreate the collection to wipe everything.
            name = self._collection.name
            self._client.delete_collection(name)
            self._collection = self._client.get_or_create_collection(name)
        else:
            self._collection.delete(where={"session_id": session_id})

    def count(self, session_id: str | None = None) -> int:
        try:
            return self._collection.count()
        except Exception:  # noqa: BLE001 - backend-specific
            return 0
