"""Tests for the Telegram bot menu, usage store and profile/report builders."""

from __future__ import annotations

import time

import pytest

from jarvis.interfaces.bot_menu import (
    profile_text,
    screen_language,
    screen_main,
    screen_memory,
    screen_model,
    screen_settings,
    subscription_text,
    usage_text,
)
from jarvis.interfaces.usage import UsageStore


# -- usage store --------------------------------------------------------------


@pytest.fixture()
def usage() -> UsageStore:
    store = UsageStore(":memory:")
    yield store
    store.close()


def test_usage_records_and_aggregates(usage):
    usage.record(1, tokens=100)
    usage.record(1, tokens=50)
    usage.record(2, tokens=999)
    s = usage.stats(1)
    assert s["messages"] == 2 and s["tokens"] == 150
    assert s["messages_today"] == 2 and s["tokens_today"] == 150
    # Other users are separate.
    assert usage.stats(2)["tokens"] == 999
    assert usage.stats(3)["tokens"] == 0


def test_usage_time_windows(usage):
    usage.record(1, tokens=10)
    # Backdate one row beyond 30 days.
    usage._conn.execute("UPDATE usage SET ts = ? WHERE tokens = 10",
                        (time.time() - 40 * 86400,))
    usage._conn.commit()
    usage.record(1, tokens=7)
    s = usage.stats(1)
    assert s["tokens"] == 17          # all time
    assert s["tokens_today"] == 7     # only the fresh one
    assert s["tokens_month"] == 7


# -- menu layout --------------------------------------------------------------


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_main_menu_minimal():
    text, rows = screen_main("en")
    assert "J.A.R.V.I.S." in text
    flat = _flat(rows)
    assert "m:profile" in flat and "m:usage" in flat
    assert "m:settings" in flat and "m:memory" in flat
    assert "m:help" in flat
    # Admin / billing absent by default.
    assert "m:admin" not in flat
    assert "m:buy" not in flat


def test_main_menu_full():
    _text, rows = screen_main("ru", is_admin=True, billing_on=True,
                            accounts_on=True, multi_model=True)
    flat = _flat(rows)
    for expected in ("m:subscription", "m:buy", "m:link", "m:admin"):
        assert expected in flat


def test_settings_and_submenus_have_back():
    _t, srows = screen_settings("en", multi_model=True)
    assert "m:model" in _flat(srows)
    assert "m:main" in _flat(srows)  # back button
    _t, mrows = screen_memory("en")
    assert "m:reset" in _flat(mrows) and "m:forget" in _flat(mrows)
    assert "m:main" in _flat(mrows)
    _t, mdl = screen_model("en", ["claude", "gpt"], "gpt")
    flat = _flat(mdl)
    assert "m:setmodel:claude" in flat and "m:setmodel:auto" in flat
    assert "m:settings" in flat  # back to settings
    _t, lang = screen_language("en", "ru")
    flat = _flat(lang)
    assert "m:setlang:ru" in flat and "m:setlang:en" in flat
    assert "m:settings" in flat


def test_settings_hides_model_when_single():
    _t, rows = screen_settings("en", multi_model=False)
    assert "m:model" not in _flat(rows)
    assert "m:language" in _flat(rows)


# -- text builders ------------------------------------------------------------


def test_profile_text_contains_fields():
    stats = {"messages": 12, "tokens": 34567}
    text = profile_text(
        "en", telegram_id=42, name="Tony", language="en", model="claude",
        account="tony", telegram_verified=True, stats=stats)
    assert "42" in text and "Tony" in text and "tony" in text
    assert "Claude" in text  # model label
    assert "34 567" in text  # thousands formatted with a space


def test_profile_text_no_account():
    stats = {"messages": 0, "tokens": 0}
    text = profile_text(
        "ru", telegram_id=1, name="X", language="ru", model="",
        account=None, telegram_verified=False, stats=stats)
    assert "не привязан" in text
    assert "Auto" in text


def test_usage_text():
    stats = {"messages": 5, "tokens": 1000, "messages_today": 2,
            "tokens_today": 400, "messages_month": 5, "tokens_month": 1000}
    text = usage_text("en", stats)
    assert "Token report" in text and "400" in text and "1 000" in text


def test_subscription_text_states():
    class Lic:
        def __init__(self, plan, expires, revoked=False):
            self.plan = plan
            self.expires_at = expires
            self._revoked = revoked

        def is_valid(self, *, now):
            return not self._revoked and (self.expires_at is None
                                        or self.expires_at > now)

    now = time.time()
    assert "no account" in subscription_text("en", account=None, licenses=[],
                                            now=now).lower()
    active = subscription_text("en", account="tony",
                            licenses=[Lic("pro", now + 10 * 86400)], now=now)
    assert "pro" in active and "days left" in active
    perpetual = subscription_text("en", account="tony",
                                licenses=[Lic("std", None)], now=now)
    assert "Lifetime" in perpetual
    inactive = subscription_text("en", account="tony",
                                licenses=[Lic("std", now - 1)], now=now)
    assert "No active" in inactive
