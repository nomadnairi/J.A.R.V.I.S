"""
OpenRouter provider — a dedicated gateway to many models (GPT, Claude, Gemini,
DeepSeek, Llama, …) through one OpenAI-compatible API.

Kept deliberately separate from the OpenAI provider: configure it with its own
``OPENROUTER_API_KEY`` / ``OPENROUTER_MODEL`` and leave ``OPENAI_*`` for the real
OpenAI. Someone who only wants ChatGPT sets OpenAI; someone who only wants
OpenRouter sets OpenRouter — no base-URL juggling, no mixing.
"""

from __future__ import annotations

from jarvis.llm.providers.openai_provider import OpenAIProvider

#: OpenRouter's OpenAI-compatible endpoint.
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter is OpenAI-compatible, so it reuses the OpenAI request path but
    always targets the OpenRouter endpoint and reports its own provider name."""

    name = "openrouter"

    def _effective_base_url(self) -> str | None:
        # Always OpenRouter (an explicit base_url may still override, e.g. a
        # regional mirror), never the OpenAI default.
        return self.base_url or DEFAULT_OPENROUTER_BASE_URL
