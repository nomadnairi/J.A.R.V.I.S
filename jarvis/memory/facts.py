"""
LLM-based fact extraction.

Instead of storing whole conversation transcripts in semantic memory (noisy),
the :class:`FactExtractor` uses the language model to pull out a few durable,
self-contained facts worth remembering — "the user's dog is named Rex", "the
user's deadline is Friday" — and returns them as short strings.

It is best-effort: any failure (no LLM, bad JSON) yields an empty list rather
than raising, so a memory hiccup never breaks a turn.
"""

from __future__ import annotations

import json

from jarvis.llm.client import LLMClient
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM = (
    "You extract durable facts worth remembering about the user from a single "
    "exchange. Return ONLY a compact JSON array of short, self-contained fact "
    "strings written in the third person (e.g. [\"The user's dog is named "
    "Rex\", \"The user lives in Berlin\"]). Include only stable, personal, or "
    "task-relevant facts — never small talk, questions, or transient details. "
    "If there is nothing worth remembering, return []."
)


class FactExtractor:
    """Extracts durable facts from a conversation turn via the LLM."""

    def __init__(self, llm: LLMClient, *, max_facts: int = 5) -> None:
        self.llm = llm
        self.max_facts = max_facts

    async def extract(self, user: str, assistant: str) -> list[str]:
        """Return a list of durable facts from a user/assistant exchange."""
        if not self.llm.has_any_provider():
            return []
        prompt = (
            f"User said: {user}\n"
            f"Assistant replied: {assistant}\n\n"
            "Extract the durable facts as a JSON array."
        )
        try:
            result = await self.llm.complete(
                [{"role": "user", "content": prompt}], system=_SYSTEM
            )
        except Exception as exc:  # noqa: BLE001 - best-effort, never break a turn
            logger.debug("Fact extraction failed: %s", exc)
            return []

        return self._parse(result.text)

    def _parse(self, text: str) -> list[str]:
        text = text.strip()
        # Tolerate models that wrap JSON in prose or code fences.
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1 or end < start:
            return []
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return []
        facts = [str(item).strip() for item in data if str(item).strip()]
        return facts[: self.max_facts]
