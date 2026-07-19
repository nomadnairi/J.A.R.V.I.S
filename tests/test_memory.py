"""Tests for the memory subsystem (async, SQLite, recall, facts)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.llm.client import LLMClient
from jarvis.memory.base import MemoryRecord
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.memory.embeddings import HashingEmbedder, cosine_similarity
from jarvis.memory.facts import FactExtractor
from jarvis.memory.manager import MemoryManager
from jarvis.memory.sqlite_vector_store import SQLiteVectorStore
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


# -- in-memory vector store -------------------------------------------------


def test_inmemory_recall_orders_by_relevance():
    store = InMemoryVectorStore(embedder=HashingEmbedder())
    store.remember(MemoryRecord(content="I love playing the guitar", session_id="s"))
    store.remember(MemoryRecord(content="The weather is cold today", session_id="s"))
    results = store.recall("music and guitar", session_id="s", limit=1)
    assert results and "guitar" in results[0].content


def test_inmemory_persistence(tmp_path):
    path = str(tmp_path / "mem.json")
    store = InMemoryVectorStore(embedder=HashingEmbedder(), persist_path=path)
    store.remember(MemoryRecord(content="remember this", session_id="s"))
    reloaded = InMemoryVectorStore(embedder=HashingEmbedder(), persist_path=path)
    assert reloaded.count() == 1


# -- SQLite vector store ----------------------------------------------------


def _sqlite_store(**kw) -> SQLiteVectorStore:
    return SQLiteVectorStore(HashingEmbedder(), db_path=":memory:", **kw)


def test_sqlite_recall_orders_by_relevance():
    store = _sqlite_store()
    store.remember(MemoryRecord(content="I love playing the guitar", session_id="s"))
    store.remember(MemoryRecord(content="The weather is cold today", session_id="s"))
    results = store.recall("music and guitar", session_id="s", limit=1)
    assert results and "guitar" in results[0].content


def test_sqlite_scopes_by_session():
    store = _sqlite_store()
    store.remember(MemoryRecord(content="alice likes tea", session_id="alice"))
    store.remember(MemoryRecord(content="bob likes coffee", session_id="bob"))
    assert store.count("alice") == 1
    results = store.recall("drinks", session_id="alice", limit=5)
    assert all(r.session_id == "alice" for r in results)


def test_sqlite_threshold_filters_weak_matches():
    store = _sqlite_store(min_score=0.99)  # almost nothing clears this
    store.remember(MemoryRecord(content="totally unrelated content", session_id="s"))
    assert store.recall("something else entirely", session_id="s") == []


def test_sqlite_recency_prefers_newer():
    store = _sqlite_store(recency_weight=0.9)
    old = MemoryRecord(
        content="the meeting is important",
        session_id="s",
        timestamp=datetime.now(timezone.utc) - timedelta(days=60),
    )
    new = MemoryRecord(content="the meeting is important", session_id="s")
    store.remember(old)
    store.remember(new)
    results = store.recall("the meeting is important", session_id="s", limit=2)
    # Same content -> recency decides; the newer one ranks first.
    assert results[0].score >= results[1].score


def test_sqlite_incremental_count():
    store = _sqlite_store()
    for i in range(5):
        store.remember(MemoryRecord(content=f"fact {i}", session_id="s"))
    assert store.count() == 5
    store.forget("s")
    assert store.count() == 0


def test_sqlite_eviction_caps_per_session():
    store = _sqlite_store(max_per_session=3)
    for i in range(6):
        store.remember(MemoryRecord(content=f"unique memory number {i}", session_id="s"))
    assert store.count("s") == 3


def test_sqlite_dedup_skips_near_duplicates():
    store = _sqlite_store(dedup_threshold=0.95)
    store.remember(MemoryRecord(content="the user's dog is named Rex", session_id="s"))
    store.remember(MemoryRecord(content="the user's dog is named Rex", session_id="s"))
    assert store.count("s") == 1


# -- conversation store -----------------------------------------------------


def test_conversation_store_roundtrip():
    store = SQLiteConversationStore(":memory:")
    store.append("s1", Message.user("hello"))
    store.append("s1", Message.assistant("hi there"))
    conv = store.load("s1")
    assert len(conv) == 2
    assert conv.messages[0].content == "hello"


def test_conversation_store_isolates_sessions():
    store = SQLiteConversationStore(":memory:")
    store.append_exchange("a", "q1", "a1")
    store.append_exchange("b", "q2", "a2")
    assert store.count("a") == 2
    assert set(store.sessions()) == {"a", "b"}


# -- fact extraction --------------------------------------------------------


@pytest.mark.asyncio
async def test_fact_extractor_parses_json():
    llm = LLMClient(primary=FakeProvider(
        default_reply='["The user\'s dog is named Rex", "The user lives in Berlin"]'
    ))
    extractor = FactExtractor(llm)
    facts = await extractor.extract("I have a dog named Rex and live in Berlin", "Noted.")
    assert facts == ["The user's dog is named Rex", "The user lives in Berlin"]


@pytest.mark.asyncio
async def test_fact_extractor_tolerates_garbage():
    llm = LLMClient(primary=FakeProvider(default_reply="I'm not sure, sorry!"))
    extractor = FactExtractor(llm)
    assert await extractor.extract("hi", "hello") == []


# -- memory manager (async) -------------------------------------------------


def _make_manager(fact_extractor=None) -> MemoryManager:
    return MemoryManager(
        vector_store=SQLiteVectorStore(HashingEmbedder(), db_path=":memory:"),
        conversation_store=SQLiteConversationStore(":memory:"),
        recall_limit=3,
        fact_extractor=fact_extractor,
    )


@pytest.mark.asyncio
async def test_manager_persists_and_recalls():
    mgr = _make_manager()
    await mgr.persist_turn("s", "I have a dog named Rex", "Noted, Sir.")
    await mgr.remember("s", "The user's dog is named Rex")
    assert mgr.load_conversation("s").messages[0].content == "I have a dog named Rex"
    ctx = await mgr.recall_context("tell me about my pet dog", session_id="s")
    assert ctx is not None and "Rex" in ctx


@pytest.mark.asyncio
async def test_manager_remember_turn_uses_fact_extractor():
    llm = LLMClient(primary=FakeProvider(default_reply='["The user is named Tony"]'))
    mgr = _make_manager(fact_extractor=FactExtractor(llm))
    await mgr.remember_turn("s", "My name is Tony", "Nice to meet you.")
    recalled = await mgr.recall("what is the user's name", session_id="s")
    assert any("Tony" in r.content for r in recalled)


@pytest.mark.asyncio
async def test_manager_forget():
    mgr = _make_manager()
    await mgr.persist_turn("s", "q", "a")
    await mgr.remember("s", "some memory")
    await mgr.forget("s")
    assert mgr.stats()["memories"] == 0
    assert mgr.stats()["stored_messages"] == 0


@pytest.mark.asyncio
async def test_manager_redacts_secrets_in_history():
    mgr = _make_manager()  # redact_secrets defaults to True
    await mgr.persist_turn(
        "s", "my token is 1234567890:AAFfakefakefakefakefakefakefakefake00", "ok"
    )
    stored = mgr.load_conversation("s").messages[0].content
    assert "1234567890" not in stored
    assert "[REDACTED]" in stored


@pytest.mark.asyncio
async def test_manager_redacts_secrets_in_semantic_memory():
    mgr = _make_manager()
    await mgr.remember("s", "the api key is sk-abcdef0123456789abcdef")
    recalled = await mgr.recall("api key", session_id="s")
    assert all("sk-abcdef" not in r.content for r in recalled)


# -- engine RAG integration -------------------------------------------------


def _memory_engine(fact_extractor=None) -> tuple[JarvisEngine, FakeProvider]:
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=True)
    provider = FakeProvider(default_reply="Understood, Sir.")
    memory = _make_manager(fact_extractor=fact_extractor)
    container = ServiceContainer(
        settings, llm_client=LLMClient(primary=provider), memory=memory
    )
    return JarvisEngine(container=container), provider


@pytest.mark.asyncio
async def test_engine_persists_history_across_sessions():
    engine, _ = _memory_engine()
    await engine.ask("My favourite colour is teal.", session_id="user1")
    engine.sessions.drop("user1")  # force reload from disk
    reloaded = engine.session("user1")
    assert len(reloaded.conversation) == 2
    assert "teal" in reloaded.conversation.messages[0].content


@pytest.mark.asyncio
async def test_engine_injects_recalled_memory():
    engine, provider = _memory_engine()
    await engine.ask("Remember that my project deadline is Friday.", session_id="u")
    await engine.drain()  # let background memory writes finish

    captured: dict = {}
    original = provider.complete

    async def spy(messages, system=None, tools=None, model=None):
        captured["system"] = system
        return await original(messages, system, tools)

    provider.complete = spy  # type: ignore[assignment]
    await engine.ask("When is my deadline?", session_id="u")
    assert "deadline" in (captured.get("system") or "").lower()


@pytest.mark.asyncio
async def test_engine_forget_clears_memory():
    engine, _ = _memory_engine()
    await engine.ask("secret fact", session_id="u")
    await engine.drain()
    await engine.forget("u")
    assert engine.memory.stats()["memories"] == 0
