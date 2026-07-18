"""Tests for the Stage 2 memory subsystem."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.core.engine import JarvisEngine
from jarvis.core.container import ServiceContainer
from jarvis.llm.client import LLMClient
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.memory.embeddings import HashingEmbedder, cosine_similarity
from jarvis.memory.manager import MemoryManager
from jarvis.memory.vector_store import InMemoryVectorStore
from jarvis.models.message import Message
from tests.conftest import FakeProvider


# -- embeddings -------------------------------------------------------------


def test_hashing_embedder_is_deterministic():
    emb = HashingEmbedder(dimensions=64)
    assert emb.embed("hello world") == emb.embed("hello world")
    assert len(emb.embed("hello world")) == 64


def test_similar_text_scores_higher():
    emb = HashingEmbedder()
    a = emb.embed("the cat sat on the mat")
    close = emb.embed("a cat sat on a mat")
    far = emb.embed("quantum chromodynamics equations")
    assert cosine_similarity(a, close) > cosine_similarity(a, far)


# -- vector store -----------------------------------------------------------


def test_vector_store_recall_orders_by_relevance():
    from jarvis.memory.base import MemoryRecord

    store = InMemoryVectorStore(embedder=HashingEmbedder())
    store.remember(MemoryRecord(content="I love playing the guitar", session_id="s"))
    store.remember(MemoryRecord(content="The weather is cold today", session_id="s"))

    results = store.recall("music and guitar", session_id="s", limit=1)
    assert results
    assert "guitar" in results[0].content


def test_vector_store_scopes_by_session():
    from jarvis.memory.base import MemoryRecord

    store = InMemoryVectorStore(embedder=HashingEmbedder())
    store.remember(MemoryRecord(content="alice likes tea", session_id="alice"))
    store.remember(MemoryRecord(content="bob likes coffee", session_id="bob"))

    assert store.count("alice") == 1
    results = store.recall("drinks", session_id="alice", limit=5)
    assert all(r.session_id == "alice" for r in results)


def test_vector_store_persistence(tmp_path):
    from jarvis.memory.base import MemoryRecord

    path = str(tmp_path / "mem.json")
    store = InMemoryVectorStore(embedder=HashingEmbedder(), persist_path=path)
    store.remember(MemoryRecord(content="remember this", session_id="s"))

    reloaded = InMemoryVectorStore(embedder=HashingEmbedder(), persist_path=path)
    assert reloaded.count() == 1


# -- conversation store -----------------------------------------------------


def test_conversation_store_roundtrip():
    store = SQLiteConversationStore(":memory:")
    store.append("s1", Message.user("hello"))
    store.append("s1", Message.assistant("hi there"))
    conv = store.load("s1")
    assert len(conv) == 2
    assert conv.messages[0].content == "hello"
    assert conv.messages[1].content == "hi there"


def test_conversation_store_isolates_sessions():
    store = SQLiteConversationStore(":memory:")
    store.append_exchange("a", "q1", "a1")
    store.append_exchange("b", "q2", "a2")
    assert store.count("a") == 2
    assert store.count("b") == 2
    assert set(store.sessions()) == {"a", "b"}


def test_conversation_store_clear():
    store = SQLiteConversationStore(":memory:")
    store.append_exchange("a", "q", "a")
    store.clear("a")
    assert store.count("a") == 0


# -- memory manager ---------------------------------------------------------


def _make_manager() -> MemoryManager:
    return MemoryManager(
        vector_store=InMemoryVectorStore(embedder=HashingEmbedder()),
        conversation_store=SQLiteConversationStore(":memory:"),
        recall_limit=3,
    )


def test_manager_persists_and_recalls():
    mgr = _make_manager()
    mgr.persist_turn("s", "I have a dog named Rex", "Noted, Sir.")
    mgr.remember("s", "User said: I have a dog named Rex\nYou replied: Noted, Sir.")

    # History persisted.
    assert mgr.load_conversation("s").messages[0].content == "I have a dog named Rex"
    # Semantic recall finds it.
    ctx = mgr.recall_context("tell me about my pet dog", session_id="s")
    assert ctx is not None
    assert "Rex" in ctx


def test_manager_forget():
    mgr = _make_manager()
    mgr.persist_turn("s", "q", "a")
    mgr.remember("s", "some memory")
    mgr.forget("s")
    assert mgr.stats()["memories"] == 0
    assert mgr.stats()["stored_messages"] == 0


# -- engine RAG integration -------------------------------------------------


def _memory_engine() -> tuple[JarvisEngine, FakeProvider]:
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=True)
    provider = FakeProvider(default_reply="Understood, Sir.")
    memory = _make_manager()
    container = ServiceContainer(
        settings, llm_client=LLMClient(primary=provider), memory=memory
    )
    return JarvisEngine(container=container), provider


@pytest.mark.asyncio
async def test_engine_persists_history_across_sessions():
    engine, _ = _memory_engine()
    await engine.ask("My favourite colour is teal.", session_id="user1")
    # Drop the in-memory session; a fresh get_or_create must reload from disk.
    engine.sessions.drop("user1")
    reloaded = engine.session("user1")
    assert len(reloaded.conversation) == 2
    assert "teal" in reloaded.conversation.messages[0].content


@pytest.mark.asyncio
async def test_engine_injects_recalled_memory(monkeypatch):
    engine, provider = _memory_engine()
    await engine.ask("Remember that my project deadline is Friday.", session_id="u")

    # The next LLM call should receive recalled memory in the system prompt.
    captured: dict = {}
    original = provider.complete

    async def spy(messages, system=None, tools=None):
        captured["system"] = system
        return await original(messages, system, tools)

    provider.complete = spy  # type: ignore[assignment]
    await engine.ask("When is my deadline?", session_id="u")

    assert "deadline" in (captured.get("system") or "").lower()


@pytest.mark.asyncio
async def test_engine_forget_clears_memory():
    engine, _ = _memory_engine()
    await engine.ask("secret fact", session_id="u")
    await engine.forget("u")
    assert engine.memory.stats()["memories"] == 0
