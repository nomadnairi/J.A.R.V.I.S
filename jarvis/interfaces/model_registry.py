"""
Model Registry — the single source of truth for the model marketplace.

Every client (Telegram, desktop, web) reads models from here, so the catalog,
search, categories, providers, popular/free lists, comparison and rating all
come from one place. Adding a :class:`ModelCard` makes the model appear
everywhere automatically — no UI code changes.

The registry is framework-free and fully testable; the curated seed below is
plain data an operator can edit. Live OpenRouter models (the long tail) are
handled separately by :mod:`jarvis.interfaces.model_search`.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

# --- taxonomy ---------------------------------------------------------------

#: Category id -> (emoji, English label). Labels are localised in the UI layer.
CATEGORIES: dict[str, tuple[str, str]] = {
    "coding": ("💻", "Coding"),
    "reasoning": ("🧠", "Reasoning"),
    "long_context": ("📚", "Long context"),
    "fast": ("⚡", "Fast"),
    "free": ("🆓", "Free"),
    "vision": ("🎨", "Vision"),
    "multilingual": ("🌍", "Multilingual"),
    "writing": ("📖", "Writing"),
    "research": ("🔬", "Research"),
}

#: Provider id -> display name.
PROVIDERS: dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "meta": "Meta",
    "mistral": "Mistral",
    "xai": "xAI",
}

STATUS_STABLE, STATUS_BETA, STATUS_EXPERIMENTAL = "stable", "beta", "experimental"


@dataclass(frozen=True)
class ModelCard:
    """Full metadata for one model — the marketplace card."""

    slug: str            # OpenRouter model id (routing key)
    name: str
    provider: str        # key in PROVIDERS
    context: int         # context window, tokens
    categories: tuple[str, ...]
    vision: bool
    tools: bool          # tool / function calling
    cost: int            # 0..4 ($ scale; 0 = free)
    speed: int           # 1..5
    quality: int         # 1..5
    free: bool
    popular: bool
    rating: int          # higher = higher in the TOP list
    status: str = STATUS_STABLE
    strengths: tuple[str, ...] = ()
    summary: str = ""

    @property
    def emoji(self) -> str:
        return {"anthropic": "🧠", "openai": "💬", "google": "🌐",
                "deepseek": "🐋", "qwen": "🐦", "meta": "🦙",
                "mistral": "🌬", "xai": "🤖"}.get(self.provider, "🤖")

    @property
    def cost_label(self) -> str:
        return "🆓" if self.free or self.cost == 0 else "$" * max(1, self.cost)

    def stars(self, value: int) -> str:
        return "★" * value + "☆" * (5 - value)


# --- curated seed (edit freely) --------------------------------------------

REGISTRY: list[ModelCard] = [
    ModelCard("anthropic/claude-sonnet-4", "Claude Sonnet 4", "anthropic",
            200_000, ("coding", "reasoning", "long_context", "writing"),
            vision=True, tools=True, cost=3, speed=4, quality=5,
            free=False, popular=True, rating=96,
            strengths=("coding", "code analysis", "long documents", "reasoning"),
            summary="Anthropic's balanced flagship — excellent at code and analysis."),
    ModelCard("anthropic/claude-opus-4", "Claude Opus 4", "anthropic",
            200_000, ("reasoning", "coding", "research", "writing"),
            vision=True, tools=True, cost=4, speed=3, quality=5,
            free=False, popular=True, rating=95,
            strengths=("deep reasoning", "hard coding", "research"),
            summary="Top-tier reasoning and the hardest tasks; slower and pricier."),
    ModelCard("anthropic/claude-3.7-sonnet", "Claude 3.7 Sonnet", "anthropic",
            200_000, ("coding", "reasoning", "long_context"),
            vision=True, tools=True, cost=3, speed=4, quality=5,
            free=False, popular=True, rating=90,
            strengths=("coding", "reasoning", "documents"),
            summary="Great all-rounder for coding and analysis."),
    ModelCard("anthropic/claude-3.5-haiku", "Claude 3.5 Haiku", "anthropic",
            200_000, ("fast", "coding"),
            vision=False, tools=True, cost=1, speed=5, quality=4,
            free=False, popular=False, rating=80,
            strengths=("speed", "cheap", "everyday tasks"),
            summary="Fast and cheap for quick, high-volume tasks."),
    ModelCard("openai/gpt-4o", "GPT-4o", "openai",
            128_000, ("reasoning", "vision", "multilingual", "writing"),
            vision=True, tools=True, cost=3, speed=4, quality=5,
            free=False, popular=True, rating=92,
            strengths=("multimodal", "general", "writing"),
            summary="OpenAI's versatile multimodal flagship."),
    ModelCard("openai/gpt-4o-mini", "GPT-4o mini", "openai",
            128_000, ("fast", "vision"),
            vision=True, tools=True, cost=1, speed=5, quality=4,
            free=False, popular=True, rating=84,
            strengths=("speed", "cheap", "multimodal"),
            summary="Small, fast, cheap — a great default."),
    ModelCard("openai/o1", "o1", "openai",
            200_000, ("reasoning", "research"),
            vision=False, tools=False, cost=4, speed=2, quality=5,
            free=False, popular=False, rating=88,
            strengths=("math", "logic", "planning"),
            summary="Deliberate reasoning for math and hard logic; slower."),
    ModelCard("google/gemini-2.5-pro", "Gemini 2.5 Pro", "google",
            1_000_000, ("long_context", "reasoning", "vision", "multilingual"),
            vision=True, tools=True, cost=3, speed=4, quality=5,
            free=False, popular=True, rating=91,
            strengths=("huge context", "vision", "multilingual"),
            summary="Massive 1M context with strong all-round quality."),
    ModelCard("google/gemini-2.5-flash", "Gemini 2.5 Flash", "google",
            1_000_000, ("fast", "long_context", "vision"),
            vision=True, tools=True, cost=1, speed=5, quality=4,
            free=False, popular=True, rating=85,
            strengths=("speed", "huge context", "cheap"),
            summary="Fast, cheap, and a huge context window."),
    ModelCard("deepseek/deepseek-r1", "DeepSeek R1", "deepseek",
            128_000, ("reasoning", "coding"),
            vision=False, tools=True, cost=1, speed=3, quality=5,
            free=False, popular=True, rating=89,
            strengths=("reasoning", "math", "cheap"),
            summary="Open reasoning model rivalling the big labs, at low cost."),
    ModelCard("deepseek/deepseek-chat", "DeepSeek V3", "deepseek",
            128_000, ("coding", "multilingual"),
            vision=False, tools=True, cost=1, speed=4, quality=4,
            free=False, popular=True, rating=83,
            strengths=("coding", "cheap", "general"),
            summary="Strong, inexpensive general and coding model."),
    ModelCard("qwen/qwen-2.5-72b-instruct", "Qwen 2.5 72B", "qwen",
            131_072, ("coding", "multilingual", "reasoning"),
            vision=False, tools=True, cost=1, speed=4, quality=4,
            free=False, popular=False, rating=80,
            strengths=("multilingual", "coding"),
            summary="Capable multilingual model, strong on code."),
    ModelCard("x-ai/grok-2-1212", "Grok 2", "xai",
            131_072, ("reasoning", "writing", "multilingual"),
            vision=False, tools=True, cost=3, speed=4, quality=4,
            free=False, popular=False, rating=81,
            strengths=("writing", "reasoning", "current events"),
            summary="xAI's conversational model with a lively style."),
    ModelCard("mistralai/mistral-large", "Mistral Large", "mistral",
            128_000, ("coding", "multilingual", "reasoning"),
            vision=False, tools=True, cost=2, speed=4, quality=4,
            free=False, popular=False, rating=79,
            strengths=("multilingual", "coding", "EU-hosted"),
            summary="Mistral's flagship — strong multilingual and coding."),
    ModelCard("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B", "meta",
            131_072, ("free", "multilingual", "coding"),
            vision=False, tools=True, cost=0, speed=4, quality=4,
            free=True, popular=True, rating=82,
            strengths=("open", "free", "multilingual"),
            summary="Open-weights workhorse, available free on OpenRouter."),
    ModelCard("google/gemini-2.0-flash-001", "Gemini 2.0 Flash", "google",
            1_000_000, ("free", "fast", "vision"),
            vision=True, tools=True, cost=0, speed=5, quality=4,
            free=True, popular=True, rating=81,
            strengths=("free", "fast", "huge context"),
            summary="Free, fast, huge context — great for everyday use."),
]

_BY_SLUG = {m.slug: m for m in REGISTRY}


# --- queries ----------------------------------------------------------------

def all_models() -> list[ModelCard]:
    return list(REGISTRY)


def get(slug: str) -> ModelCard | None:
    return _BY_SLUG.get(slug)


def search(query: str, *, limit: int = 20) -> list[ModelCard]:
    q = (query or "").strip().lower()
    if not q:
        return all_models()[:limit]
    hits = [m for m in REGISTRY
            if q in m.name.lower() or q in m.slug.lower()
            or q in m.provider.lower()]
    return sorted(hits, key=lambda m: -m.rating)[:limit]


def by_category(category: str, *, limit: int = 20) -> list[ModelCard]:
    hits = [m for m in REGISTRY if category in m.categories]
    return sorted(hits, key=lambda m: -m.rating)[:limit]


def by_provider(provider: str, *, limit: int = 50) -> list[ModelCard]:
    hits = [m for m in REGISTRY if m.provider == provider]
    return sorted(hits, key=lambda m: -m.rating)[:limit]


def free_models(*, limit: int = 20) -> list[ModelCard]:
    return sorted((m for m in REGISTRY if m.free),
                key=lambda m: -m.rating)[:limit]


def popular(*, limit: int = 10) -> list[ModelCard]:
    return sorted((m for m in REGISTRY if m.popular),
                key=lambda m: -m.rating)[:limit]


def top_rated(*, limit: int = 10) -> list[ModelCard]:
    return sorted(REGISTRY, key=lambda m: -m.rating)[:limit]


def providers_with_models() -> list[tuple[str, str, int]]:
    """(provider_id, display_name, count) for providers that have models."""
    out = []
    for pid, name in PROVIDERS.items():
        n = sum(1 for m in REGISTRY if m.provider == pid)
        if n:
            out.append((pid, name, n))
    return out


# --- favourites (per user) --------------------------------------------------

class FavoritesStore:
    """Per-user favourite models (SQLite)."""

    def __init__(self, db_path: str = "data/jarvis.db") -> None:
        self._lock = threading.Lock()
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS favorites ("
            "user_id TEXT NOT NULL, slug TEXT NOT NULL, "
            "PRIMARY KEY (user_id, slug))")
        self._conn.commit()

    def toggle(self, user_id: int | str, slug: str) -> bool:
        """Add/remove a favourite; returns True if it's now a favourite."""
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND slug = ?",
                (str(user_id), slug)).fetchone()
            if row:
                self._conn.execute(
                    "DELETE FROM favorites WHERE user_id = ? AND slug = ?",
                    (str(user_id), slug))
                self._conn.commit()
                return False
            self._conn.execute(
                "INSERT INTO favorites (user_id, slug) VALUES (?, ?)",
                (str(user_id), slug))
            self._conn.commit()
            return True

    def list(self, user_id: int | str) -> list[ModelCard]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT slug FROM favorites WHERE user_id = ?",
                (str(user_id),)).fetchall()
        cards = [get(r[0]) for r in rows]
        return [c for c in cards if c is not None]

    def is_favorite(self, user_id: int | str, slug: str) -> bool:
        with self._lock:
            return self._conn.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND slug = ?",
                (str(user_id), slug)).fetchone() is not None

    def close(self) -> None:  # pragma: no cover - lifecycle
        with self._lock:
            self._conn.close()
