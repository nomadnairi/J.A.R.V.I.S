"""
Text embedders.

Two backends:

* :class:`HashingEmbedder` — dependency-free, deterministic embeddings via the
  hashing trick. Captures lexical overlap well enough for recall, works
  offline, and needs no API key. This is the default.
* :class:`OpenAIEmbedder` — high-quality semantic embeddings via the OpenAI
  embeddings API. Optional; requires ``OPENAI_API_KEY`` and the ``openai``
  package.
"""

from __future__ import annotations

import hashlib
import math

from jarvis.memory.base import BaseEmbedder
from jarvis.utils.exceptions import MemoryError as JarvisMemoryError
from jarvis.utils.text import tokenize_words


class HashingEmbedder(BaseEmbedder):
    """Deterministic bag-of-words embedding using feature hashing.

    Each token is hashed into a bucket; the vector is L2-normalised. Similar
    texts (shared vocabulary) land close together under cosine similarity.
    """

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def _bucket(self, token: str) -> tuple[int, float]:
        # Non-cryptographic: MD5 only buckets tokens into embedding dimensions.
        # usedforsecurity=False makes that explicit for security scanners.
        digest = hashlib.md5(  # noqa: S324
            token.encode("utf-8"), usedforsecurity=False
        ).digest()
        index = int.from_bytes(digest[:4], "big") % self.dimensions
        # Sign bit from a second byte keeps buckets from only ever accumulating.
        sign = 1.0 if digest[4] & 1 else -1.0
        return index, sign

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for token in tokenize_words(text):
            index, sign = self._bucket(token)
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


class OpenAIEmbedder(BaseEmbedder):
    """Semantic embeddings via the OpenAI embeddings API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        if not api_key:
            raise JarvisMemoryError("OpenAIEmbedder requires an OpenAI API key.")
        self.api_key = api_key
        self.model = model
        self.dimensions = 1536  # text-embedding-3-small
        self._client: object | None = None

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise JarvisMemoryError(
                "The 'openai' package is required for OpenAIEmbedder."
            ) from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        try:
            response = client.embeddings.create(model=self.model, input=texts)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise JarvisMemoryError(f"OpenAI embedding request failed: {exc}") from exc
        return [item.embedding for item in response.data]


class LocalEmbedder(BaseEmbedder):
    """Semantic embeddings from a local model via ``fastembed``.

    Uses ONNX-runtime models (no PyTorch), so it is far lighter than
    sentence-transformers while giving real semantic similarity — "pet" will
    match "dog". The model is downloaded on first use and cached on disk.
    ``fastembed`` is an optional dependency.
    """

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model
        self.dimensions = 384  # bge-small
        self._model: object | None = None

    def _ensure_model(self) -> object:
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise JarvisMemoryError(
                "LocalEmbedder requires the 'fastembed' package. "
                "Install it or use the default hashing embedder."
            ) from exc
        self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        return [list(map(float, vec)) for vec in model.embed(texts)]  # type: ignore[attr-defined]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
