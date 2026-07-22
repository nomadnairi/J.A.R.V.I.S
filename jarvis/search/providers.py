"""
Concrete search providers.

Each turns its backend's JSON into a list of :class:`SearchResult`. The parsing
is a pure ``parse`` staticmethod (unit-testable without the network); ``search``
just fetches then parses. Add a new backend by subclassing SearchProvider.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from jarvis.search.base import SearchProvider, SearchResult


class DuckDuckGoProvider(SearchProvider):
    """No API key required — DuckDuckGo's Instant Answer API (best-effort)."""

    name = "duckduckgo"
    label = "DuckDuckGo"
    requires_key = False
    kind = "web"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        out: list[SearchResult] = []
        for topic in raw.get("RelatedTopics", []):
            # Nested groups also appear; flatten one level.
            items = topic.get("Topics", [topic])
            for it in items:
                url = it.get("FirstURL")
                text = it.get("Text")
                if url and text:
                    out.append(SearchResult(title=text[:80], url=url,
                                            snippet=text, source="duckduckgo"))
        return out

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        url = (f"https://api.duckduckgo.com/?q={quote_plus(query)}"
            "&format=json&no_html=1&no_redirect=1")
        raw = await self._json(url)
        return self._limit(self.parse(raw), limit)


class TavilyProvider(SearchProvider):
    """Tavily — AI search API (needs TAVILY_API_KEY)."""

    name = "tavily"
    label = "Tavily"
    kind = "ai"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        return [SearchResult(title=r.get("title", ""), url=r.get("url", ""),
                            snippet=r.get("content", ""), source="tavily")
                for r in raw.get("results", []) if r.get("url")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raw = await self._json(
            "https://api.tavily.com/search", method="POST",
            payload={"api_key": self.api_key, "query": query,
                    "max_results": limit})
        return self._limit(self.parse(raw), limit)


class ExaProvider(SearchProvider):
    """Exa — neural/AI search (needs EXA_API_KEY)."""

    name = "exa"
    label = "Exa"
    kind = "ai"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        return [SearchResult(title=r.get("title") or r.get("url", ""),
                            url=r.get("url", ""),
                            snippet=(r.get("text") or "")[:400], source="exa")
                for r in raw.get("results", []) if r.get("url")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raw = await self._json(
            "https://api.exa.ai/search", method="POST",
            headers={"x-api-key": self.api_key},
            payload={"query": query, "numResults": limit, "contents": {"text": True}})
        return self._limit(self.parse(raw), limit)


class BraveProvider(SearchProvider):
    """Brave Search API (needs BRAVE_API_KEY)."""

    name = "brave"
    label = "Brave Search"
    kind = "web"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        web = (raw.get("web") or {}).get("results", [])
        return [SearchResult(title=r.get("title", ""), url=r.get("url", ""),
                            snippet=r.get("description", ""), source="brave")
                for r in web if r.get("url")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raw = await self._json(
            f"https://api.search.brave.com/res/v1/web/search"
            f"?q={quote_plus(query)}&count={limit}",
            headers={"X-Subscription-Token": self.api_key,
                    "Accept": "application/json"})
        return self._limit(self.parse(raw), limit)


class GoogleCSEProvider(SearchProvider):
    """Google Programmable Search (needs GOOGLE_CSE_KEY + GOOGLE_CSE_CX)."""

    name = "google"
    label = "Google"
    kind = "web"

    def available(self) -> bool:
        return bool(self.api_key and self.options.get("cx"))

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        return [SearchResult(title=r.get("title", ""), url=r.get("link", ""),
                            snippet=r.get("snippet", ""), source="google")
                for r in raw.get("items", []) if r.get("link")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        cx = self.options.get("cx", "")
        raw = await self._json(
            f"https://www.googleapis.com/customsearch/v1?key={self.api_key}"
            f"&cx={cx}&q={quote_plus(query)}&num={min(limit, 10)}")
        return self._limit(self.parse(raw), limit)


class SerpApiProvider(SearchProvider):
    """SerpAPI (Google results proxy; needs SERPAPI_KEY)."""

    name = "serpapi"
    label = "SerpAPI"
    kind = "web"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        return [SearchResult(title=r.get("title", ""), url=r.get("link", ""),
                            snippet=r.get("snippet", ""), source="serpapi")
                for r in raw.get("organic_results", []) if r.get("link")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raw = await self._json(
            f"https://serpapi.com/search.json?engine=google"
            f"&q={quote_plus(query)}&num={limit}&api_key={self.api_key}")
        return self._limit(self.parse(raw), limit)


#: Registry of provider classes (order = routing priority; free DDG last).
PROVIDER_CLASSES = (
    TavilyProvider, ExaProvider, BraveProvider,
    GoogleCSEProvider, SerpApiProvider, DuckDuckGoProvider,
)
