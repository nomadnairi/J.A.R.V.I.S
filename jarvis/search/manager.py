"""
Search Manager — the single entry point the AI core uses to search the web.

It owns a set of providers and a router: a named provider, or the first
available one by priority (AI-search backends first, free DuckDuckGo as the
always-available fallback). Providers are built from settings, so enabling a
backend is just adding its API key.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.config.settings import Settings
from jarvis.search.base import SearchError, SearchProvider, SearchResult
from jarvis.search.providers import (
    BraveProvider,
    DuckDuckGoProvider,
    ExaProvider,
    GoogleCSEProvider,
    PerplexityProvider,
    PlaywrightProvider,
    SerpApiProvider,
    TavilyProvider,
)

#: Human labels for the three provider categories the router knows about.
KIND_LABELS = {
    "ai": "🤖 AI search",
    "web": "🌐 Web search",
    "browser": "🧭 Browser",
}


@dataclass(frozen=True)
class ProviderStatus:
    """One provider's routing metadata + readiness."""

    name: str
    label: str
    kind: str
    requires_key: bool
    available: bool
    is_default: bool


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
            PerplexityProvider(settings.perplexity_api_key),
            BraveProvider(settings.brave_api_key),
            GoogleCSEProvider(settings.google_cse_key, cx=settings.google_cse_cx),
            SerpApiProvider(settings.serpapi_key),
            DuckDuckGoProvider(),      # no key — always available fallback
            PlaywrightProvider(),      # keyless browser (if Playwright installed)
        ]
        return cls(providers, default=settings.search_provider or "auto")

    def providers(self) -> list[str]:
        return list(self._order)

    def available(self) -> list[str]:
        return [n for n in self._order if self._providers[n].available()]

    # -- router introspection ---------------------------------------------

    def statuses(self) -> list[ProviderStatus]:
        """Routing metadata + readiness for every provider, in priority order."""
        out: list[ProviderStatus] = []
        for name in self._order:
            p = self._providers[name]
            out.append(ProviderStatus(
                name=name, label=getattr(p, "label", name),
                kind=getattr(p, "kind", "web"),
                requires_key=getattr(p, "requires_key", True),
                available=p.available(),
                is_default=(name == self.default)))
        return out

    def by_kind(self, kind: str) -> list[str]:
        """Provider names of a given category ('ai' / 'web' / 'browser')."""
        return [s.name for s in self.statuses() if s.kind == kind]

    def categories(self) -> dict[str, list[ProviderStatus]]:
        """Providers grouped by category, categories ordered ai → web → browser."""
        grouped: dict[str, list[ProviderStatus]] = {}
        for st in self.statuses():
            grouped.setdefault(st.kind, []).append(st)
        ordered = {}
        for kind in ("ai", "web", "browser"):
            if kind in grouped:
                ordered[kind] = grouped[kind]
        # Any unexpected kinds appended after the known ones.
        for kind, items in grouped.items():
            if kind not in ordered:
                ordered[kind] = items
        return ordered

    def active(self) -> str | None:
        """Name of the provider a default (auto) search would route to now."""
        chosen = self._pick(self.default)
        return chosen.name if chosen else None

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
