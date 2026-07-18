"""
SQLite-backed semantic vector store.

Stores :class:`MemoryRecord` items with their embedding in SQLite and recalls
them by relevance. Unlike the JSON-backed :class:`InMemoryVectorStore`, writes
are **incremental** (a single INSERT), so remembering is O(1) on disk instead
of rewriting the whole store each time.

Recall combines cosine similarity with an optional **recency** boost and drops
matches below a **similarity threshold**, so weak or stale memories don't
pollute the prompt. Similarity is still computed in Python (adequate for tens
of thousands of records); a true ANN index is a later optimisation.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import threading
from datetime import datetime, timezone
from math import exp
from pathlib import Path

from jarvis.memory.base import BaseEmbedder, BaseMemoryStore, MemoryRecord
from jarvis.memory.embeddings import cosine_similarity
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   BLOB NOT NULL,
    timestamp   TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
"""


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class SQLiteVectorStore(BaseMemoryStore):
    """A persistent vector store backed by SQLite."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        db_path: str = "data/jarvis.db",
        *,
        min_score: float = 0.15,
        recency_weight: float = 0.15,
        recency_half_life_days: float = 7.0,
    ) -> None:
        self.embedder = embedder
        self.db_path = db_path
        self.min_score = min_score
        self.recency_weight = max(0.0, min(1.0, recency_weight))
        self.recency_half_life_s = recency_half_life_days * 86400.0
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- write --------------------------------------------------------------

    def remember(self, record: MemoryRecord) -> None:
        embedding = self.embedder.embed(record.content)
        with self._lock:
            self._conn.execute(
                "INSERT INTO memories (session_id, kind, content, embedding, "
                "timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.session_id,
                    record.kind,
                    record.content,
                    _pack(embedding),
                    record.timestamp.isoformat(),
                    json.dumps(record.metadata),
                ),
            )
            self._conn.commit()

    # -- read ---------------------------------------------------------------

    def recall(self, query: str, *, session_id: str | None = "default",
            limit: int = 5) -> list[MemoryRecord]:
        q = self.embedder.embed(query)
        if session_id is None:
            sql = "SELECT * FROM memories"
            params: tuple = ()
        else:
            sql = "SELECT * FROM memories WHERE session_id = ?"
            params = (session_id,)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        now = datetime.now(timezone.utc)
        scored: list[MemoryRecord] = []
        for row in rows:
            similarity = cosine_similarity(q, _unpack(row["embedding"]))
            if similarity < self.min_score:
                continue
            final = self._apply_recency(similarity, row["timestamp"], now)
            scored.append(
                MemoryRecord(
                    content=row["content"],
                    session_id=row["session_id"],
                    kind=row["kind"],
                    score=final,
                    metadata=json.loads(row["metadata"]),
                )
            )
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    def _apply_recency(self, similarity: float, ts_iso: str,
                    now: datetime) -> float:
        if self.recency_weight <= 0.0:
            return similarity
        try:
            ts = datetime.fromisoformat(ts_iso)
        except ValueError:
            return similarity
        age = max(0.0, (now - ts).total_seconds())
        recency = exp(-age / self.recency_half_life_s)  # 1.0 (now) → 0.0 (old)
        return (1.0 - self.recency_weight) * similarity + self.recency_weight * recency

    # -- delete -------------------------------------------------------------

    def forget(self, session_id: str | None = "default") -> None:
        with self._lock:
            if session_id is None:
                self._conn.execute("DELETE FROM memories")
            else:
                self._conn.execute(
                    "DELETE FROM memories WHERE session_id = ?", (session_id,)
                )
            self._conn.commit()

    # -- introspection ------------------------------------------------------

    def count(self, session_id: str | None = None) -> int:
        with self._lock:
            if session_id is None:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM memories"
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM memories WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        return int(row["n"])

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
