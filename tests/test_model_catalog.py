"""Tests for the model catalog (tier-gated model selection via OpenRouter)."""

from __future__ import annotations

import pytest

from jarvis.interfaces import model_catalog as mc
from jarvis.interfaces.bot_menu import screen_catalog
from jarvis.interfaces.user_prefs import UserPreferences
from jarvis.llm.client import LLMClient


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_catalog_is_non_empty_and_tiered():
    assert len(mc.CATALOG) >= 6
    tiers = {m.tier for m in mc.CATALOG}
    assert {"free", "plus", "pro"} <= tiers


def test_unlocked_respects_tier_order():
    free = next(m for m in mc.CATALOG if m.tier == "free")
    pro = next(m for m in mc.CATALOG if m.tier == "pro")
    assert mc.unlocked(free, "free")
    assert not mc.unlocked(pro, "free")
    assert mc.unlocked(pro, "pro")
    assert mc.unlocked(free, "pro")  # higher tier keeps lower models


def test_pagination_covers_every_model_once():
    seen = []
    for p in range(mc.page_count()):
        seen += [idx for idx, _ in mc.page(p)]
    assert seen == list(range(len(mc.CATALOG)))


def test_screen_catalog_marks_locked_and_current():
    # A free user: pro models are locked; the chosen one is ticked.
    free_slug = next(m.slug for m in mc.CATALOG if m.tier == "free")
    text, rows = screen_catalog("en", "free", free_slug, page=0)
    assert "catalog" in text.lower() or "Model" in text
    # Every catalog entry maps to a setcat callback.
    assert any(d.startswith("m:setcat:") for d in _flat(rows))
    # Rendered labels include a lock for gated models and a tick for current.
    labels = [lbl for row in rows for lbl, _ in row]
    joined = " ".join(labels)
    assert "🔒" in joined      # at least one pro model locked for a free user
    assert "✅" in joined      # current selection ticked


@pytest.mark.asyncio
async def test_stream_threads_a_specific_model():
    # A specific catalog model must reach the provider's stream() as `model`.
    captured = {}

    class FakeProvider:
        name = "openrouter"

        def is_available(self) -> bool:
            return True

        async def stream(self, messages, system=None, model=None):
            captured["model"] = model
            yield "ok"

    provider = FakeProvider()
    client = LLMClient(provider, [], profiles={"openrouter": provider})
    chunks = [c async for c in client.stream(
        [{"role": "user", "content": "hi"}],
        profile="openrouter", model="x-ai/grok-2-1212")]
    assert chunks == ["ok"]
    assert captured["model"] == "x-ai/grok-2-1212"


def test_user_prefs_model_id_roundtrip():
    prefs = UserPreferences(":memory:")
    assert prefs.get_model_id(7) is None
    prefs.set_model_id(7, "openai/gpt-4o")
    assert prefs.get_model_id(7) == "openai/gpt-4o"
    prefs.set_model_id(7, "")           # clearing returns None
    assert prefs.get_model_id(7) is None
    prefs.close()
