"""
Curated catalog of models offered in the bot (served through OpenRouter).

BotHub-style: one OpenRouter key unlocks dozens of models; this is a hand-picked,
tier-gated shortlist so users pick from a clean menu instead of hundreds of
slugs. Edit the list freely — slugs are plain OpenRouter model ids.

Each entry declares the minimum tier that may use it, so Free users see premium
models locked (🔒) and are nudged to upgrade. Models are referenced by index in
callback data (slugs are far too long for Telegram's 64-byte limit).
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.billing import TIER_ORDER


@dataclass(frozen=True)
class CatalogModel:
    slug: str          # OpenRouter model id
    name: str          # display name
    emoji: str
    tier: str          # minimum tier: "free" | "plus" | "pro"
    note: str = ""     # short tag shown in the list (e.g. "free", "fast")


#: The shortlist, cheapest/most-open first. Editable per deployment.
CATALOG: list[CatalogModel] = [
    # --- Free tier: open / low-cost models ---
    CatalogModel("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B", "🦙",
                "free", "open"),
    CatalogModel("deepseek/deepseek-chat", "DeepSeek V3", "🌊", "free", "cheap"),
    CatalogModel("google/gemini-2.0-flash-001", "Gemini 2.0 Flash", "⚡",
                "free", "fast"),
    CatalogModel("mistralai/mistral-small-3.2-24b-instruct", "Mistral Small", "🌬",
                "free"),
    # --- Plus tier: strong mid models ---
    CatalogModel("openai/gpt-4o-mini", "GPT-4o mini", "💬", "plus"),
    CatalogModel("anthropic/claude-3.5-haiku", "Claude 3.5 Haiku", "🧠", "plus"),
    CatalogModel("deepseek/deepseek-r1", "DeepSeek R1", "🐋", "plus", "reasoning"),
    CatalogModel("google/gemini-2.5-flash", "Gemini 2.5 Flash", "✨", "plus"),
    # --- Pro tier: flagships ---
    CatalogModel("openai/gpt-4o", "GPT-4o", "💬", "pro"),
    CatalogModel("anthropic/claude-3.7-sonnet", "Claude 3.7 Sonnet", "🧠", "pro"),
    CatalogModel("google/gemini-2.5-pro", "Gemini 2.5 Pro", "🌐", "pro"),
    CatalogModel("x-ai/grok-2-1212", "Grok 2", "🤖", "pro"),
]

PAGE_SIZE = 6


def unlocked(model: CatalogModel, user_tier: str) -> bool:
    """Whether ``user_tier`` is high enough to use ``model``."""
    def rank(t: str) -> int:
        return TIER_ORDER.index(t) if t in TIER_ORDER else 0
    return rank(user_tier) >= rank(model.tier)


def by_slug(slug: str) -> CatalogModel | None:
    return next((m for m in CATALOG if m.slug == slug), None)


def page_count() -> int:
    return max(1, (len(CATALOG) + PAGE_SIZE - 1) // PAGE_SIZE)


def page(index: int) -> list[tuple[int, CatalogModel]]:
    """Return ``(catalog_index, model)`` pairs for page ``index`` (0-based)."""
    index = max(0, min(index, page_count() - 1))
    start = index * PAGE_SIZE
    return [(i, CATALOG[i]) for i in range(start, min(start + PAGE_SIZE, len(CATALOG)))]
