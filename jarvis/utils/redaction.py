"""
Secret redaction.

Strips obvious secrets (API keys, bot tokens, card-like numbers) from text
before it is persisted to memory, so credentials a user happens to paste are
never stored in the conversation history or the semantic memory.

This is a best-effort filter, not a security boundary — it catches common
patterns, not every possible secret.
"""

from __future__ import annotations

import re

_PLACEHOLDER = "[REDACTED]"

# Order matters: more specific patterns first.
_PATTERNS: tuple[re.Pattern, ...] = (
    # Telegram bot token: 123456789:AA... (35+ char secret part)
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"),
    # Anthropic / OpenAI style keys: sk-..., sk-ant-...
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}\b"),
    # AWS access key id
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Bearer tokens
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"),
    # key/token/secret/password = value
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd)\b\s*[=:]\s*\S{6,}"
    ),
    # Card-like sequences of 13–19 digits (optionally separated).
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)


def redact_secrets(text: str) -> str:
    """Return ``text`` with recognised secrets replaced by ``[REDACTED]``."""
    if not text:
        return text
    redacted = text
    for pattern in _PATTERNS:
        redacted = pattern.sub(_PLACEHOLDER, redacted)
    return redacted


def contains_secret(text: str) -> bool:
    """Whether ``text`` appears to contain a recognised secret."""
    return redact_secrets(text) != text
