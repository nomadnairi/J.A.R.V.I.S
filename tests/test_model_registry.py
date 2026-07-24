"""Tests for the Model Registry (marketplace foundation)."""

from __future__ import annotations

from jarvis.interfaces import model_registry as mr


def test_registry_is_populated_and_consistent():
    models = mr.all_models()
    assert len(models) >= 12
    for m in models:
        assert m.provider in mr.PROVIDERS
        assert 1 <= m.quality <= 5 and 1 <= m.speed <= 5
        assert all(c in mr.CATEGORIES for c in m.categories)
        assert m.status in (mr.STATUS_STABLE, mr.STATUS_BETA, mr.STATUS_EXPERIMENTAL)


def test_get_by_slug():
    m = mr.get("anthropic/claude-sonnet-4")
    assert m is not None and m.name == "Claude Sonnet 4"
    assert mr.get("does/not-exist") is None


def test_search_matches_name_provider_slug():
    assert any(m.provider == "anthropic" for m in mr.search("claude"))
    assert any("deepseek" in m.slug for m in mr.search("deepseek"))
    assert mr.search("gpt")  # by name
    assert mr.search("zzz-nope") == []


def test_category_and_provider_filters():
    coders = mr.by_category("coding")
    assert coders and all("coding" in m.categories for m in coders)
    anthropic = mr.by_provider("anthropic")
    assert anthropic and all(m.provider == "anthropic" for m in anthropic)


def test_free_popular_and_top_lists():
    assert all(m.free for m in mr.free_models())
    assert all(m.popular for m in mr.popular())
    top = mr.top_rated(limit=5)
    assert len(top) == 5
    # Sorted by rating, descending.
    assert [m.rating for m in top] == sorted((m.rating for m in top), reverse=True)


def test_providers_with_models_counts():
    provs = dict((pid, n) for pid, _name, n in mr.providers_with_models())
    assert provs.get("anthropic", 0) >= 2
    assert all(n > 0 for n in provs.values())


def test_card_labels():
    free = next(m for m in mr.all_models() if m.free)
    assert free.cost_label == "🆓"
    paid = mr.get("anthropic/claude-opus-4")
    assert paid.cost_label.startswith("$")
    assert paid.stars(5) == "★★★★★"


def test_favorites_toggle_and_list():
    store = mr.FavoritesStore(":memory:")
    slug = "openai/gpt-4o"
    assert store.is_favorite(1, slug) is False
    assert store.toggle(1, slug) is True         # added
    assert store.is_favorite(1, slug) is True
    assert [m.slug for m in store.list(1)] == [slug]
    assert store.toggle(1, slug) is False        # removed
    assert store.list(1) == []
    store.close()
