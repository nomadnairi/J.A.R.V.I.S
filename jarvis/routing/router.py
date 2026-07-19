"""
Model-tier router.

Given the user's message, decides whether a fast/cheap model or a strong model
should handle it. The heuristic is intentionally simple and transparent: longer
messages, code, and reasoning/planning cues push toward the strong tier.
"""

from __future__ import annotations

import re
from enum import Enum

from jarvis.config.settings import Settings
from jarvis.utils.text import tokenize_words


class ModelTier(str, Enum):
    FAST = "fast"
    STRONG = "strong"


# Words that signal a task needs stronger reasoning.
_STRONG_CUES = {
    "why", "explain", "analyze", "analyse", "plan", "design", "architect",
    "debug", "compare", "refactor", "optimize", "optimise", "prove", "derive",
    "strategy", "reason", "translate", "summarize", "summarise", "code",
}
_CODE_RE = re.compile(r"```|def |function |class |import |select |=>|;\s*$", re.MULTILINE)


class AIRouter:
    """Routes a request to a model tier and resolves it to a model name."""

    def __init__(self, fast_model: str, strong_model: str, *,
                enabled: bool = False, word_threshold: int = 40) -> None:
        self.fast_model = fast_model
        self.strong_model = strong_model
        self.enabled = enabled and bool(fast_model) and bool(strong_model)
        self.word_threshold = word_threshold

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIRouter":
        base = settings.llm_model
        return cls(
            fast_model=settings.llm_model_fast or base,
            strong_model=settings.llm_model_strong or base,
            enabled=settings.ai_router_enabled,
            word_threshold=settings.router_word_threshold,
        )

    # -- decisions ----------------------------------------------------------

    def tier(self, text: str) -> ModelTier:
        """Classify ``text`` into a model tier."""
        words = tokenize_words(text)
        if len(words) >= self.word_threshold:
            return ModelTier.STRONG
        if _STRONG_CUES & set(words):
            return ModelTier.STRONG
        if _CODE_RE.search(text):
            return ModelTier.STRONG
        if text.count("?") >= 2:  # several questions at once
            return ModelTier.STRONG
        return ModelTier.FAST

    def model_for(self, text: str) -> str | None:
        """Return the model name to use, or None to keep the provider default.

        Returns None when routing is disabled, so callers pass no override.
        """
        if not self.enabled:
            return None
        return (self.strong_model if self.tier(text) == ModelTier.STRONG
                else self.fast_model)
