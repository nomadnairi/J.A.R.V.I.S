"""Concrete LLM provider implementations."""

from jarvis.llm.providers.anthropic_provider import AnthropicProvider
from jarvis.llm.providers.openai_provider import OpenAIProvider

#: Registry mapping provider name -> class.
PROVIDER_REGISTRY = {
    AnthropicProvider.name: AnthropicProvider,
    OpenAIProvider.name: OpenAIProvider,
}

__all__ = ["AnthropicProvider", "OpenAIProvider", "PROVIDER_REGISTRY"]
