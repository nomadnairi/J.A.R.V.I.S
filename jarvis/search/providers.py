"""
Concrete search providers.

Each turns its backend's JSON into a list of :class:`SearchResult`. The parsing
is a pure ``parse`` staticmethod (unit-testable without the network); ``search``
just fetches then parses. Add a new backend by subclassing SearchProvider.
"""

from __future__ import annotations

import html as _html
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit

from jarvis.search.base import SearchProvider, SearchResult


class DuckDuckGoProvider(SearchProvider):
    """Keyless web search — DuckDuckGo's HTML endpoint (real results, no key).

    The old Instant-Answer API returned almost nothing for ordinary queries;
    this scrapes the same HTML results page a browser would get, so search
    works out of the box without any API key.
    """

    name = "duckduckgo"
    label = "DuckDuckGo"
    requires_key = False
    kind = "web"

    _RESULT = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
    _SNIPPET = re.compile(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.S)

    @staticmethod
    def _clean_url(href: str) -> str:
        href = _html.unescape(href)
        if href.startswith("//"):
            href = "https:" + href
        # DDG wraps targets in /l/?uddg=<url-encoded real url>.
        if "uddg=" in href:
            uddg = parse_qs(urlsplit(href).query).get("uddg")
            if uddg:
                return unquote(uddg[0])
        return href

    @classmethod
    def parse(cls, page: str) -> list[SearchResult]:
        def strip(s: str) -> str:
            return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        snippets = [strip(s) for s in cls._SNIPPET.findall(page)]
        out: list[SearchResult] = []
        for i, (href, title) in enumerate(cls._RESULT.findall(page)):
            url = cls._clean_url(href)
            if not url:
                continue
            out.append(SearchResult(
                title=strip(title)[:120] or url, url=url,
                snippet=(snippets[i] if i < len(snippets) else "")[:400],
                source="duckduckgo"))
        return out

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        page = await self._text("https://html.duckduckgo.com/html/",
                                method="POST", form={"q": query})
        return self._limit(self.parse(page), limit)


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


class PerplexityProvider(SearchProvider):
    """Perplexity — an AI answer engine with cited sources (needs a key)."""

    name = "perplexity"
    label = "Perplexity"
    kind = "ai"

    @staticmethod
    def parse(raw: dict) -> list[SearchResult]:
        choices = raw.get("choices") or []
        answer = ""
        if choices:
            answer = (choices[0].get("message") or {}).get("content", "") or ""
        citations = [c for c in (raw.get("citations") or []) if c]
        out: list[SearchResult] = []
        if answer:
            out.append(SearchResult(
                title="🔮 Perplexity answer",
                url=citations[0] if citations else "",
                snippet=answer[:600], source="perplexity"))
        for i, url in enumerate(citations, 1):
            out.append(SearchResult(title=f"Source {i}", url=url,
                                    snippet="", source="perplexity"))
        return out

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raw = await self._json(
            "https://api.perplexity.ai/chat/completions", method="POST",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={"model": "sonar",
                    "messages": [{"role": "user", "content": query}]})
        return self._limit(self.parse(raw), limit)


class PlaywrightProvider(SearchProvider):
    """Keyless browser search — drives headless Chromium to scrape results.

    Only "available" when Playwright is installed; otherwise the router skips it.
    """

    name = "playwright"
    label = "Browser (Playwright)"
    requires_key = False
    kind = "browser"

    def available(self) -> bool:
        try:
            import playwright  # noqa: F401
        except Exception:  # noqa: BLE001 - optional dependency
            return False
        return True

    @staticmethod
    def parse(items: list[dict]) -> list[SearchResult]:
        """Turn scraped ``{title,url,snippet}`` dicts into results (pure)."""
        return [SearchResult(title=(i.get("title") or "").strip(),
                            url=i.get("url", ""),
                            snippet=(i.get("snippet") or "").strip(),
                            source="playwright")
                for i in items if i.get("url")]

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        items = await self._scrape(query, limit)
        return self._limit(self.parse(items), limit)

    async def _scrape(self, query: str, limit: int) -> list[dict]:  # pragma: no cover - needs a browser
        from playwright.async_api import async_playwright

        items: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(f"https://duckduckgo.com/html/?q={quote_plus(query)}",
                                timeout=20000)
                anchors = await page.query_selector_all("a.result__a")
                for a in anchors[:limit]:
                    items.append({
                        "title": await a.inner_text(),
                        "url": await a.get_attribute("href") or "",
                        "snippet": "",
                    })
            finally:
                await browser.close()
        return items


#: Registry of provider classes (order = routing priority).
#: AI answer engines first, classic web next, keyless fallbacks last.
PROVIDER_CLASSES = (
    TavilyProvider, ExaProvider, PerplexityProvider, BraveProvider,
    GoogleCSEProvider, SerpApiProvider, DuckDuckGoProvider, PlaywrightProvider,
)
