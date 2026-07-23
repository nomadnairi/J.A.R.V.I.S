"""Tests for the Search Provider Manager introspection + bot screen."""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.interfaces.bot_menu import screen_search_providers, screen_settings
from jarvis.search.manager import SearchManager


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_statuses_carry_kind_and_readiness():
    mgr = SearchManager.from_settings(Settings(log_file="", tavily_api_key="k"))
    by_name = {s.name: s for s in mgr.statuses()}
    assert by_name["tavily"].kind == "ai" and by_name["tavily"].available
    assert by_name["duckduckgo"].kind == "web"
    assert by_name["duckduckgo"].requires_key is False
    assert by_name["playwright"].kind == "browser"


def test_categories_grouped_ai_web_browser():
    mgr = SearchManager.from_settings(Settings(log_file=""))
    cats = mgr.categories()
    assert list(cats.keys())[:2] == ["ai", "web"]
    assert "perplexity" in [s.name for s in cats["ai"]]
    assert "playwright" in [s.name for s in cats["browser"]]


def test_by_kind_filters():
    mgr = SearchManager.from_settings(Settings(log_file=""))
    assert set(mgr.by_kind("ai")) == {"tavily", "exa", "perplexity"}
    assert "duckduckgo" in mgr.by_kind("web")


def test_active_routes_to_ddg_without_keys():
    mgr = SearchManager.from_settings(Settings(log_file=""))
    assert mgr.active() == "duckduckgo"
    mgr2 = SearchManager.from_settings(Settings(log_file="", tavily_api_key="k"))
    assert mgr2.active() == "tavily"


def test_screen_shows_categories_and_active_star():
    mgr = SearchManager.from_settings(Settings(log_file="", brave_api_key="k",
                                            search_provider="brave"))
    text, rows = screen_search_providers("en", mgr.statuses(), mgr.active())
    assert "Web search" in text and "AI search" in text
    assert "⭐" in text                       # active provider starred
    assert "m:settings" in _flat(rows)        # back to settings
    assert "m:close" in _flat(rows)


def test_settings_tools_exposes_search_button_only_when_enabled():
    from jarvis.interfaces.bot_menu import screen_settings_tools
    _t, on = screen_settings_tools("en", search_on=True, mcp_on=False)
    assert "m:searchprov" in _flat(on)
    _t2, off = screen_settings_tools("en", search_on=False, mcp_on=False)
    assert "m:searchprov" not in _flat(off)
    # And the hub surfaces the Tools category when search is on.
    _t3, hub = screen_settings("en", search_on=True)
    assert "m:settools" in _flat(hub)
