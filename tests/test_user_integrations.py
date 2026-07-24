"""Tests for per-user integrations: store, tier limit, validation."""

from __future__ import annotations

import pytest

from jarvis.billing.plans import default_plans
from jarvis.interfaces.user_integrations import (
    UserIntegrationsStore,
    integration_limit_reached,
    validate,
)


def test_limit_by_tier():
    plans = default_plans()
    # Free allows 2.
    assert integration_limit_reached(plans["free"], 1) is False
    assert integration_limit_reached(plans["free"], 2) is True
    # Plus allows 6.
    assert integration_limit_reached(plans["plus"], 5) is False
    assert integration_limit_reached(plans["plus"], 6) is True
    # Pro is unlimited.
    assert integration_limit_reached(plans["pro"], 999) is False


def test_store_add_list_remove_count():
    store = UserIntegrationsStore(":memory:")
    assert store.count(1) == 0
    iid = store.add(1, "webhook", "My hook", {"url": "https://x/hook"})
    assert store.count(1) == 1
    items = store.list(1)
    assert items[0].kind == "webhook" and items[0].config["url"] == "https://x/hook"
    # Scoped per user.
    assert store.count(2) == 0
    assert store.remove(iid, 1) is True and store.count(1) == 0
    assert store.remove(iid, 1) is False


@pytest.mark.asyncio
async def test_validate_homeassistant():
    class OkHttp:
        async def get_json(self, url, headers=None):
            return {"message": "API running."}

    ok, _ = await validate("homeassistant",
                        {"url": "https://ha.local", "token": "t"}, http=OkHttp())
    assert ok is True

    bad, msg = await validate("homeassistant", {"url": "", "token": ""})
    assert bad is False and "required" in msg


def test_bot_screen_shows_add_or_upsell():
    from jarvis.interfaces.bot_menu import screen_user_integrations

    def flat(rows):
        return [d for row in rows for _, d in row]

    # Under the limit → add buttons.
    _t, rows = screen_user_integrations("ru", [(1, "🏠 HA")], 1, "6",
                                        at_limit=False)
    f = flat(rows)
    assert "m:intadd:homeassistant" in f and "m:intdel:1" in f
    assert "m:plans" not in f
    # At the limit → upsell to plans, no add buttons.
    _t2, rows2 = screen_user_integrations("ru", [], 2, "2", at_limit=True)
    f2 = flat(rows2)
    assert "m:plans" in f2 and "m:intadd:homeassistant" not in f2


@pytest.mark.asyncio
async def test_validate_webhook_requires_https():
    ok, _ = await validate("webhook", {"url": "https://x/hook"})
    assert ok is True
    bad, _ = await validate("webhook", {"url": "http://x/hook"})
    assert bad is False
