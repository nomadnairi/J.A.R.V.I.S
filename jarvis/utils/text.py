"""Small text-processing helpers used across the codebase."""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Collapse whitespace and strip surrounding spaces."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def truncate(text: str, max_chars: int = 120, suffix: str = "…") -> str:
    """Truncate ``text`` to ``max_chars`` characters, adding ``suffix``."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)].rstrip() + suffix


def tokenize_words(text: str) -> list[str]:
    """Return lowercase word tokens (letters/digits) from ``text``."""
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def strip_wake_word(text: str, wake_words: tuple[str, ...]) -> str:
    """Remove a leading wake word (e.g. 'jarvis') from an utterance."""
    stripped = text.strip()
    lowered = stripped.lower()
    for word in wake_words:
        if lowered.startswith(word.lower()):
            rest = stripped[len(word):].lstrip(" ,.:!")
            return rest or stripped
    return stripped
