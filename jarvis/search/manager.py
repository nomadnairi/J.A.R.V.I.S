"""
Search Manager — the single entry point the AI core uses to search the web.

It owns a set of providers and a router: a named provider, or the first
available one by priority (AI-search backends first, free DuckDuckGo as the
always-available fallback). Providers are built from settings, so enabling a
backend is just adding its API key.
"""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.search.base import SearchError, SearchProvider, SearchResult
from jarvis.search.providers import (
    BraveProvider,
    DuckDuckGoProvider,
    ExaProvider,
    GoogleCSEProvider,
    SerpApiProvider,
    TavilyProvider,
)


class SearchManager:
    """Routes a query to a search provider and returns normalised results."""

    def __init__(self, providers: list[SearchProvider], *,
                default: str = "auto") -> None:
        self._providers: dict[str, SearchProvider] = {p.name: p for p in providers}
        self._order: list[str] = [p.name for p in providers]
        self.default = default

    @classmethod
    def from_settings(cls, settings: Settings) -> "SearchManager":
        providers: list[SearchProvider] = [
            TavilyProvider(settings.tavily_api_key),
            ExaProvider(settings.exa_api_key),
            BraveProvider(settings.brave_api_key),
            GoogleCSEProvider(settings.google_cse_key, cx=settings.google_cse_cx),
            SerpApiProvider(settings.serpapi_key),
            DuckDuckGoProvider(),  # no key — always available fallback
        ]
        return cls(providers, default=settings.search_provider or "auto")

    def providers(self) -> list[str]:
        return list(self._order)

    def available(self) -> list[str]:
        return [n for n in self._order if self._providers[n].available()]

    def _pick(self, name: str | None) -> SearchProvider | None:
        if name and name != "auto":
            provider = self._providers.get(name)
            return provider if provider and provider.available() else None
        for n in self._order:
            if self._providers[n].available():
                return self._providers[n]
        return None

    async def search(self, query: str, *, provider: str | None = None,
                    limit: int = 5) -> list[SearchResult]:
        """Search ``query`` via a named or the best available provider."""
        chosen = self._pick(provider or self.default)
        if chosen is None:
            raise SearchError("No search provider is available (configure a key).")
        return await chosen.search(query, limit=limit)
