"""Concrete LLM provider implementations."""

from jarvis.llm.providers.anthropic_provider import AnthropicProvider
from jarvis.llm.providers.local_provider import LocalProvider
from jarvis.llm.providers.openai_provider import OpenAIProvider
from jarvis.llm.providers.openrouter_provider import OpenRouterProvider

#: Registry mapping provider name -> class.
PROVIDER_REGISTRY = {
    AnthropicProvider.name: AnthropicProvider,
    OpenAIProvider.name: OpenAIProvider,
    OpenRouterProvider.name: OpenRouterProvider,
    LocalProvider.name: LocalProvider,
}

__all__ = [
    "AnthropicProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "LocalProvider",
    "PROVIDER_REGISTRY",
]
