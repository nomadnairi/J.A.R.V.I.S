"""
Tool manager.

A governance facade over the :class:`~jarvis.skills.registry.SkillRegistry`:
lists the tools exposed to the LLM, groups them by category, and can disable
one. Categories are inferred from each tool's module, so no per-tool wiring is
needed.
"""

from __future__ import annotations

from jarvis.skills.base import BaseSkill
from jarvis.skills.registry import SkillRegistry

_CATEGORY_BY_MODULE = {
    "jarvis.goals": "goals",
    "jarvis.files": "files",
    "jarvis.coding": "coding",
    "jarvis.desktop": "desktop",
    "jarvis.integrations": "integrations",
    "jarvis.agents": "agents",
    "jarvis.skills.builtin": "builtin",
}


class ToolManager:
    """Introspection and governance over the registered tools."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    @staticmethod
    def category_of(skill: BaseSkill) -> str:
        module = type(skill).__module__
        for prefix, category in _CATEGORY_BY_MODULE.items():
            if module.startswith(prefix):
                return category
        return "general"

    def tools(self) -> list[BaseSkill]:
        """Skills exposed to the LLM as tools (those with a parameters schema)."""
        return [s for s in self.registry.all() if s.parameters is not None]

    def categories(self) -> dict[str, list[str]]:
        """Map category -> tool names, sorted."""
        grouped: dict[str, list[str]] = {}
        for skill in self.tools():
            grouped.setdefault(self.category_of(skill), []).append(skill.name)
        return {k: sorted(v) for k, v in sorted(grouped.items())}

    def disable(self, name: str) -> bool:
        """Remove a tool by name. Returns True if it existed."""
        existed = self.registry.get(name) is not None
        self.registry.unregister(name)
        return existed

    def count(self) -> int:
        return len(self.tools())
