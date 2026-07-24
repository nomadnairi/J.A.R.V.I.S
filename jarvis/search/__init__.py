"""Web / AI search: a provider-agnostic Search Manager for the AI core."""

from jarvis.search.base import SearchError, SearchProvider, SearchResult
from jarvis.search.manager import SearchManager

__all__ = ["SearchManager", "SearchProvider", "SearchResult", "SearchError"]
