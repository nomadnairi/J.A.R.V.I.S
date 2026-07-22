"""
Search OpenRouter's model list by name / "free" / "paid".

Fetches the public OpenRouter models list (cached), normalises it, and offers a
pure ``search`` filter. Falls back to the curated static catalog when the live
list can't be fetched, so search always returns something.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from dataclasses import dataclass

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_FREE_WORDS = {"free", "бесплатно", "бесплатные", "бесплатный", "tekin", "бесплат"}
_PAID_WORDS = {"paid", "платные", "платно", "платный", "pullik"}


@dataclass(frozen=True)
class FoundModel:
    slug: str
    name: str
    free: bool
    description: str = ""

    @property
    def hint(self) -> str:
        """A short 'best for …' tag derived from the model's name/description."""
        return model_hint(self)


# Keyword → short "best for" tag. Checked in order against name + description.
_HINTS = (
    (("coder", "code", "codestral", "deepseek-coder", "devstral"),
    "🧑‍💻 coding"),
    (("reason", "-r1", "o1", "o3", "o4", "thinking", "qwq", "math"),
    "🧠 reasoning / math"),
    (("vision", "-vl", "image", "multimodal", "vl-"),
    "👁 vision / images"),
    (("mini", "flash", "haiku", "small", "lite", "8b", "7b"),
    "⚡ fast & cheap"),
    (("opus", "gpt-4o", "sonnet", "-pro", "large", "70b", "405b", "ultra"),
    "🏆 top quality"),
)


def model_hint(model: "FoundModel") -> str:
    hay = f"{model.slug} {model.name} {model.description}".lower()
    for needles, tag in _HINTS:
        if any(n in hay for n in needles):
            return tag
    return "💬 general chat"


def _is_free(model: dict) -> bool:
    if str(model.get("id", "")).endswith(":free"):
        return True
    pricing = model.get("pricing") or {}
    def zero(v) -> bool:
        try:
            return float(v) == 0.0
        except (TypeError, ValueError):
            return False
    return zero(pricing.get("prompt", 1)) and zero(pricing.get("completion", 1))


def normalize(raw_models: list[dict]) -> list[FoundModel]:
    """Turn OpenRouter ``/models`` data into :class:`FoundModel` entries."""
    out: list[FoundModel] = []
    for m in raw_models:
        slug = str(m.get("id", "")).strip()
        if not slug:
            continue
        desc = str(m.get("description") or "").strip()
        out.append(FoundModel(slug, str(m.get("name") or slug), _is_free(m), desc))
    return out


def search(models: list[FoundModel], query: str, *, limit: int = 8) -> list[FoundModel]:
    """Filter ``models`` by a query: 'free', 'paid', or a name/slug substring."""
    q = (query or "").strip().lower()
    if not q:
        return models[:limit]
    if q in _FREE_WORDS:
        res = [m for m in models if m.free]
    elif q in _PAID_WORDS:
        res = [m for m in models if not m.free]
    else:
        res = [m for m in models if q in m.name.lower() or q in m.slug.lower()]
    # Free models first, then alphabetical — nicer to scan.
    res.sort(key=lambda m: (not m.free, m.name.lower()))
    return res[:limit]


def _catalog_fallback() -> list[FoundModel]:
    from jarvis.interfaces.model_catalog import CATALOG
    return [FoundModel(m.slug, f"{m.name}", m.tier == "free") for m in CATALOG]


class ModelIndex:
    """Cached, searchable index of OpenRouter models (TTL-refreshed)."""

    def __init__(self, base_url: str = "https://openrouter.ai/api/v1",
                ttl: float = 3600.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._ttl = ttl
        self._models: list[FoundModel] = []
        self._fetched_at = 0.0

    def _fetch_blocking(self) -> list[FoundModel]:
        url = f"{self._base_url}/models"
        if not url.startswith("https://"):  # defensive: only https
            return []
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
        return normalize(data.get("data", []))

    async def all(self) -> list[FoundModel]:
        """Return the model list, refreshing from OpenRouter when stale."""
        if self._models and (time.time() - self._fetched_at) < self._ttl:
            return self._models
        try:
            models = await asyncio.to_thread(self._fetch_blocking)
        except Exception as exc:  # noqa: BLE001 - fall back to the static catalog
            logger.warning("OpenRouter model list fetch failed: %s", exc)
            models = []
        if not models:
            models = self._models or _catalog_fallback()
        self._models = models
        self._fetched_at = time.time()
        return models

    async def search(self, query: str, *, limit: int = 8) -> list[FoundModel]:
        return search(await self.all(), query, limit=limit)
