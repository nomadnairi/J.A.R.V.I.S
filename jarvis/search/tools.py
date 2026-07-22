"""Web-search tool — exposes the Search Manager to the LLM as a gated tool."""

from __future__ import annotations

from jarvis.search.base import SearchError
from jarvis.search.manager import SearchManager
from jarvis.skills.base import BaseSkill, SkillResult


class WebSearchSkill(BaseSkill):
    """Let the model look things up on the web via the Search Manager."""

    name = "web_search"
    description = ("Search the web for current information and return a short "
                "list of titled results with URLs and snippets.")
    priority = 20
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "limit": {"type": "integer",
                    "description": "Max results (default 5)."},
        },
        "required": ["query"],
    }

    def __init__(self, manager: SearchManager) -> None:
        self.manager = manager

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()

    async def execute(self, query: str = "", limit: int = 5,
                    **_: object) -> SkillResult:
        if not query.strip():
            return SkillResult(text="Please provide a search query.")
        try:
            results = await self.manager.search(query, limit=max(1, min(limit, 10)))
        except SearchError as exc:
            return SkillResult(text=f"Search unavailable: {exc}")
        if not results:
            return SkillResult(text=f"No results for {query!r}.")
        lines = [f"{i}. {r.title}\n   {r.url}\n   {r.snippet[:200]}"
                for i, r in enumerate(results, 1)]
        return SkillResult(text="\n".join(lines))


def search_skills(manager: SearchManager) -> list[BaseSkill]:
    return [WebSearchSkill(manager)]
