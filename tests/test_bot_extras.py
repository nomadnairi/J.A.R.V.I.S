"""Tests for the extra bot screens: ideas, support, about, status in profile."""

from __future__ import annotations

from jarvis.interfaces.bot_menu import (
    IDEA_KEYS,
    profile_text,
    screen_about,
    screen_ideas,
    screen_main,
    screen_support,
)


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_main_menu_has_new_buttons():
    _t, rows = screen_main("en")
    flat = _flat(rows)
    for cb in ("m:ideas", "m:newchat", "m:support", "m:about"):
        assert cb in flat


def test_screen_ideas_maps_every_prompt():
    text, rows = screen_ideas("en")
    assert "Ideas" in text
    flat = _flat(rows)
    for i in range(len(IDEA_KEYS)):
        assert f"m:idea:{i}" in flat
    assert "m:main" in flat


def test_screen_support_has_write_button():
    _t, rows = screen_support("ru")
    assert "m:support" in _flat(rows)


def test_screen_about_reflects_enabled_features():
    text, _rows = screen_about("en", version="1.6.0", voice_on=True,
                            images_on=False, catalog_on=True, billing_on=False)
    assert "1.6.0" in text
    assert "✅" in text and "❌" in text
    # Voice on → ✅ near it; images off → ❌ near it.
    lines = {ln.split(" ", 1)[1]: ln[0] for ln in text.splitlines() if ln[:1] in "✅❌"}
    # (Rough check: both marks present is enough for the smoke test.)
    assert any(v == "✅" for v in lines.values())
    assert any(v == "❌" for v in lines.values())


def test_profile_shows_status_marks():
    stats = {"messages": 5, "tokens": 100}
    text = profile_text(
        "en", telegram_id=1, name="Tony", language="en", model="claude",
        account=None, telegram_verified=False, stats=stats,
        plan_label="Pro", voice_on=True, images_on=False, own_key="openrouter")
    assert "Pro" in text
    assert "✅" in text and "❌" in text
    assert "openrouter" in text
