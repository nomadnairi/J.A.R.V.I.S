"""
Search provider framework — a common contract for every web/AI search backend.

The model never touches the internet directly; it asks the
:class:`~jarvis.search.manager.SearchManager`, which routes to one of these
providers. Adding a provider is a subclass + a registry entry — no core changes.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlsplit

from jarvis.utils.exceptions import JarvisError


class SearchError(JarvisError):
    """Raised when a search request fails."""


@dataclass(frozen=True)
class SearchResult:
    """One normalised search hit, whatever the backend."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""

    def as_dict(self) -> dict:
        return {"title": self.title, "url": self.url,
                "snippet": self.snippet, "source": self.source}


def request_json(url: str, *, method: str = "GET", headers: dict | None = None,
                payload: dict | None = None, timeout: int = 15) -> dict:
    """Blocking JSON HTTP request (call via :func:`asyncio.to_thread`)."""
    if not url.startswith("https://"):  # defensive: only https
        raise SearchError("Refusing non-https search request.")
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, method=method, data=data,
                                headers={"User-Agent": "jarvis", **(headers or {})})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  # nosec B310
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        # Some providers carry the API key in the query string; never surface
        # the full URL in an error — report only scheme+host.
        host = urlsplit(url).netloc or "search endpoint"
        raise SearchError(f"HTTP request to {host} failed: {type(exc).__name__}") \
            from exc


class SearchProvider(ABC):
    """Base class for a search backend."""

    name: str = "base"
    label: str = "Base"
    #: Whether this provider needs an API key to work.
    requires_key: bool = True
    #: "ai" (LLM-grounded), "web" (classic web search) or "browser".
    kind: str = "web"

    def __init__(self, api_key: str = "", **options: str) -> None:
        self.api_key = api_key
        self.options = options

    def available(self) -> bool:
        return bool(self.api_key) if self.requires_key else True

    @staticmethod
    def _limit(results: list[SearchResult], limit: int) -> list[SearchResult]:
        return results[: max(1, limit)]

    async def _json(self, url: str, **kw) -> dict:
        return await asyncio.to_thread(request_json, url, **kw)

    @abstractmethod
    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        """Return up to ``limit`` results for ``query``."""
        raise NotImplementedError
