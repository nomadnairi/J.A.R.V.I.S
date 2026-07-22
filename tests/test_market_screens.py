"""Tests for the Telegram model-marketplace screens."""

from __future__ import annotations

from jarvis.interfaces import model_registry as mr
from jarvis.interfaces.bot_menu import (
    screen_categories,
    screen_compare,
    screen_market_hub,
    screen_market_list,
    screen_model_card,
    screen_providers,
)


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_hub_has_all_sections():
    _t, rows = screen_market_hub("en")
    flat = _flat(rows)
    for cb in ("m:mktsearch", "m:mktpop", "m:mktfree", "m:mkttop",
            "m:mktcats", "m:mktprovs", "m:mktfavs", "m:mktcmp"):
        assert cb in flat


def test_market_list_links_cards_by_registry_index():
    cards = mr.popular()
    text, rows = screen_market_list("en", "Popular", cards)
    assert cards[0].name in text or "Popular" in text
    idx = mr.index_of(cards[0].slug)
    assert f"m:mktcard:{idx}" in _flat(rows)
    # Empty list degrades gracefully.
    empty_text, empty_rows = screen_market_list("en", "Nothing", [])
    assert "market" in " ".join(_flat(empty_rows))


def test_categories_and_providers_screens():
    _t, crows = screen_categories("en")
    assert any(d.startswith("m:mktcat:") for d in _flat(crows))
    _t2, prows = screen_providers("en")
    assert any(d.startswith("m:mktprov:") for d in _flat(prows))


def test_model_card_has_actions_and_fields():
    card = mr.get("anthropic/claude-sonnet-4")
    text, rows = screen_model_card("en", card, is_fav=False, can_use=True)
    assert "Claude Sonnet 4" in text and "Anthropic" in text
    assert "200K" in text          # context
    flat = _flat(rows)
    idx = mr.index_of(card.slug)
    assert f"m:mktuse:{idx}" in flat
    assert f"m:mktfav:{idx}" in flat
    assert f"m:mktcmpadd:{idx}" in flat
    # Without OpenRouter the "use" button is hidden.
    _t, rows2 = screen_model_card("en", card, can_use=False)
    assert f"m:mktuse:{idx}" not in _flat(rows2)


def test_compare_screen():
    empty_text, _r = screen_compare("en", [])
    assert "Comparison" in empty_text
    cards = [mr.get("openai/gpt-4o"), mr.get("anthropic/claude-sonnet-4")]
    text, rows = screen_compare("en", cards)
    assert "GPT-4o" in text and "Claude Sonnet 4" in text
    assert "m:mktcmpclear" in _flat(rows)
