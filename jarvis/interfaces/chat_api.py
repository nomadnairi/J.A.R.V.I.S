"""
Parse the in-chat ``api`` command.

Users can manage their AI without the menu by typing, for example:

    api sk-or-v1-...              → connect an OpenRouter key (auto-detected)
    api deepseek                  → search models named "deepseek"
    api free                      → list free models
    api openrouter/gpt-4o mini    → search (provider prefix is ignored)
    api                           → show help

The parser is pure and returns a small tuple the bot layer acts on.
"""

from __future__ import annotations

_PREFIXES = ("api", "апи")
#: Key prefix → provider. Order matters (most specific first).
_KEY_PREFIXES = (("sk-ant-", "anthropic"), ("sk-or-", "openrouter"),
                ("sk-", "openai"))
#: Leading noise stripped from a search query.
_LEADS = ("openrouter/", "openrouter ", "openai/", "openai ", "anthropic/",
        "anthropic ", "or/")


def detect_key_provider(token: str) -> str | None:
    """Provider for an API key by its prefix, or None if it isn't a key."""
    for prefix, provider in _KEY_PREFIXES:
        if token.startswith(prefix) and len(token) >= 20:
            return provider
    return None


def parse_api_command(text: str) -> tuple[str, str, str] | None:
    """Parse an ``api`` message.

    Returns one of:
      ("key", provider, key)   — connect this key
      ("search", query, "")    — search models
      ("help", "", "")         — show usage
    or ``None`` when the message isn't an ``api`` command.
    """
    t = (text or "").strip()
    low = t.lower()
    prefix = next(
        (p for p in _PREFIXES
        if low == p or low.startswith(p + " ") or low.startswith(p + "=")
        or low.startswith(p + ":")),
        None,
    )
    if prefix is None:
        return None

    after = t[len(prefix):]
    # "api = …" / "api: …" (any spacing) is an explicit command.
    explicit = after.lstrip()[:1] in ("=", ":")
    rest = after.lstrip(" =:").strip()
    if not rest:
        return ("help", "", "")

    # A key anywhere in the text wins — connect it.
    for token in rest.split():
        provider = detect_key_provider(token)
        if provider:
            return ("key", provider, token)

    # Otherwise a model search; drop a leading provider prefix.
    query = rest
    low_rest = rest.lower()
    for lead in _LEADS:
        if low_rest.startswith(lead):
            query = rest[len(lead):].strip()
            break
    # Guard against hijacking a normal question that merely starts with "api"
    # (e.g. "api documentation for stripe"): only a short query, or an explicit
    # "api = …" / "api: …", is treated as a search.
    if not explicit and len(query.split()) > 4:
        return None
    return ("search", query, "")
