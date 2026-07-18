"""A skill that answers date/time questions locally (no LLM call)."""

from __future__ import annotations

from datetime import datetime

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.text import tokenize_words

_TIME_TRIGGERS = {"time", "clock"}
_DATE_TRIGGERS = {"date", "today", "day"}


class DateTimeSkill(BaseSkill):
    """Reports the current date/time, both as a fast-path skill and a tool."""

    name = "get_datetime"
    description = "Get the current date and/or time on the host machine."
    priority = 50
    parameters = {
        "type": "object",
        "properties": {
            "part": {
                "type": "string",
                "enum": ["time", "date", "both"],
                "description": "Which part to return.",
            }
        },
    }

    def can_handle(self, text: str) -> bool:
        tokens = set(tokenize_words(text))
        asks_question = bool({"what", "whats", "tell"} & tokens)
        mentions_dt = bool((_TIME_TRIGGERS | _DATE_TRIGGERS) & tokens)
        return asks_question and mentions_dt

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        tokens = set(tokenize_words(text))
        part = "time" if _TIME_TRIGGERS & tokens else "date"
        return await self.execute(part=part)

    async def execute(self, part: str = "both", **_: object) -> SkillResult:
        now = datetime.now()
        if part == "time":
            return SkillResult(text=f"It is {now.strftime('%H:%M')}.")
        if part == "date":
            return SkillResult(text=f"Today is {now.strftime('%A, %d %B %Y')}.")
        return SkillResult(
            text=f"It is {now.strftime('%H:%M')} on {now.strftime('%A, %d %B %Y')}."
        )
