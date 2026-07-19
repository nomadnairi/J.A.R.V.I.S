"""A skill that lists the assistant's currently available skills."""

from __future__ import annotations

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.text import tokenize_words

_TRIGGERS = {"help", "capabilities", "skills", "commands"}


class HelpSkill(BaseSkill):
    """Handles 'what can you do' / 'help' requests.

    Fast-path only (not exposed as an LLM tool). The registry is injected
    after construction so the skill can enumerate its siblings without a
    circular import.
    """

    name = "help"
    description = "List available skills and capabilities."
    priority = 60
    parameters = None  # meta-skill: not advertised to the model

    def __init__(self) -> None:
        # Set by the container after all skills are registered.
        self.registry = None  # type: ignore[assignment]

    def can_handle(self, text: str) -> bool:
        tokens = set(tokenize_words(text))
        if _TRIGGERS & tokens:
            return True
        # "what can you do"
        return {"what"} <= tokens and bool({"do", "can"} & tokens)

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        lines = ["Here's what I can handle directly, Sir:"]
        skills = self.registry.all() if self.registry else []
        for skill in sorted(skills, key=lambda s: s.priority, reverse=True):
            if skill.description:
                tool = " (tool)" if skill.parameters is not None else ""
                lines.append(f"• {skill.name}{tool}: {skill.description}")
        lines.append(
            "Anything else, I'll reason through with the language model."
        )
        return SkillResult(text="\n".join(lines))
