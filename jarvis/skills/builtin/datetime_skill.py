"""A skill that answers date/time questions locally (no LLM call)."""

from __future__ import annotations

from datetime import datetime

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.text import tokenize_words

_TIME_TRIGGERS = {"time", "clock"}
_DATE_TRIGGERS = {"date", "today", "day"}


class DateTimeSkill(BaseSkill):
    """Handles 'what time is it' / 'what's the date' style requests."""

    name = "datetime"
    description = "Report the current date and time."
    priority = 50

    def can_handle(self, text: str) -> bool:
        tokens = set(tokenize_words(text))
        asks_question = bool({"what", "whats", "tell"} & tokens)
        mentions_dt = bool((_TIME_TRIGGERS | _DATE_TRIGGERS) & tokens)
        return asks_question and mentions_dt

    def handle(self, text: str, context: dict | None = None) -> SkillResult:
        tokens = set(tokenize_words(text))
        now = datetime.now()
        if _TIME_TRIGGERS & tokens:
            return SkillResult(text=f"It is {now.strftime('%H:%M')}.")
        return SkillResult(
            text=f"Today is {now.strftime('%A, %d %B %Y')}."
        )
