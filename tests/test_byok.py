"""Tests for bring-your-own-key (BYOK): storage, routing, and the screen."""

from __future__ import annotations

import pytest

from jarvis.interfaces.bot_menu import screen_byok
from jarvis.interfaces.user_prefs import UserPreferences


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_byok_prefs_roundtrip():
    prefs = UserPreferences(":memory:")
    assert prefs.get_byok(1) is None
    prefs.set_byok(1, "openrouter", "sk-or-secret", "openai/gpt-4o")
    got = prefs.get_byok(1)
    assert got == {"provider": "openrouter", "key": "sk-or-secret",
                "model": "openai/gpt-4o"}
    prefs.clear_byok(1)
    assert prefs.get_byok(1) is None
    prefs.close()


def test_screen_byok_offers_providers_and_disconnect():
    _t, rows = screen_byok("en", current_provider=None)
    flat = _flat(rows)
    assert "m:byokset:openai" in flat and "m:byokset:openrouter" in flat
    assert "m:byokoff" not in flat            # nothing to disconnect yet
    _t2, rows2 = screen_byok("en", current_provider="openrouter")
    assert "m:byokoff" in _flat(rows2)


@pytest.mark.asyncio
async def test_engine_routes_through_byok_provider(engine, monkeypatch):
    # With a BYOK provider in scratch, the turn must go through it, not the
    # engine's default client provider.
    from jarvis.core.engine import JarvisEngine

    captured = {}

    class FakeProvider:
        name = "openrouter"

        def is_available(self) -> bool:
            return True

        async def complete(self, messages, system=None, tools=None, model=None):
            from jarvis.llm.base import LLMResult
            captured["used"] = True
            return LLMResult(text="from your key", model="m", provider=self.name)

        def continuation_messages(self, *a, **k):
            return []

    monkeypatch.setattr(JarvisEngine, "_byok_provider",
                        lambda self, session: FakeProvider())

    from jarvis.models.response import Request
    session = engine.session("tg-99")
    session.scratch["byok"] = {"provider": "openrouter", "key": "sk-or-x",
                            "model": "openai/gpt-4o"}
    resp = await engine.process(Request(text="hello", session_id="tg-99"))
    assert captured.get("used") is True
    assert resp.text == "from your key"
