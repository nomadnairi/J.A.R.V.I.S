"""
Unified async LLM client.

Wraps one or more :class:`~jarvis.llm.base.LLMProvider` instances behind a
single interface, adding:

* async ``complete`` (with tool calling) and async ``stream``,
* automatic retry with exponential backoff (transient failures), and
* provider fallback — if the primary provider fails, configured fallbacks are
  tried in order before giving up.

The rest of the system talks only to this class.
"""

from __future__ import annotations

from typing import AsyncIterator

from jarvis.config.settings import Settings
from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.providers import PROVIDER_REGISTRY
from jarvis.llm.tools import ToolResult, ToolSpec
from jarvis.utils.exceptions import (
    AllProvidersFailedError,
    LLMConfigError,
    LLMError,
)
from jarvis.utils.logger import get_logger
from jarvis.utils.retry import retry_async

logger = get_logger(__name__)


class LLMClient:
    """Provider-agnostic async client with retry and fallback."""

    def __init__(
        self,
        primary: LLMProvider,
        fallbacks: list[LLMProvider] | None = None,
        *,
        retry_attempts: int = 3,
        profiles: "dict[str, LLMProvider] | None" = None,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []
        self._retry_attempts = retry_attempts
        #: Named, switchable providers (e.g. "claude", "gpt", "openrouter").
        self.profiles: dict[str, LLMProvider] = profiles or {}

    def list_profiles(self) -> list[str]:
        """Names of the configured, switchable model profiles."""
        return list(self.profiles)

    def _select(self, profile: str | None) -> LLMProvider | None:
        """Return the provider for a profile name, or ``None`` to use the chain."""
        if profile and profile in self.profiles:
            return self.profiles[profile]
        return None

    # -- construction from settings ----------------------------------------

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMClient":
        """Build a client from :class:`Settings`.

        The primary provider is ``settings.llm_provider``; any *other*
        provider with credentials configured is registered as a fallback.
        """
        primary = cls._make_provider(settings, settings.llm_provider,
                                    settings.llm_model)

        fallbacks: list[LLMProvider] = []
        for name in PROVIDER_REGISTRY:
            if name == settings.llm_provider:
                continue
            key = (settings.anthropic_api_key if name == "anthropic"
                else settings.openai_api_key)
            if key:
                fallbacks.append(cls._make_provider(settings, name))

        return cls(primary, fallbacks,
                profiles=cls._build_profiles(settings))

    @staticmethod
    def _build_profiles(settings: Settings) -> dict[str, LLMProvider]:
        """One switchable profile per configured provider/key.

        - ``claude``     — Anthropic (needs ANTHROPIC_API_KEY)
        - ``gpt``        — OpenAI (needs OPENAI_API_KEY)
        - ``openrouter`` — OpenAI-compatible via OpenRouter (OPENROUTER_API_KEY)
        """
        from jarvis.config.constants import DEFAULT_MODELS
        from jarvis.llm.providers.openai_provider import OpenAIProvider

        profiles: dict[str, LLMProvider] = {}
        if settings.anthropic_api_key:
            profiles["claude"] = PROVIDER_REGISTRY["anthropic"](
                api_key=settings.anthropic_api_key,
                model=DEFAULT_MODELS.get("anthropic", ""),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        if settings.openai_api_key:
            profiles["gpt"] = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=DEFAULT_MODELS.get("openai", ""),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                base_url=settings.openai_base_url,
            )
        if settings.openrouter_api_key:
            profiles["openrouter"] = OpenAIProvider(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                base_url="https://openrouter.ai/api/v1",
            )
        return profiles

    @staticmethod
    def _make_provider(settings: Settings, name: str,
                    model: str | None = None) -> LLMProvider:
        provider_cls = PROVIDER_REGISTRY.get(name)
        if provider_cls is None:
            raise LLMConfigError(f"Unknown LLM provider: {name!r}")

        from jarvis.config.constants import DEFAULT_MODELS
        key = (settings.anthropic_api_key if name == "anthropic"
            else settings.openai_api_key)
        base_url = settings.openai_base_url if name == "openai" else ""
        return provider_cls(
            api_key=key,
            model=model or DEFAULT_MODELS.get(name, ""),
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            base_url=base_url,
        )

    # -- completion ---------------------------------------------------------

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        profile: str | None = None,
    ) -> LLMResult:
        """Complete ``messages``, retrying and falling back as needed.

        ``model`` optionally overrides the provider's default model for this
        call (used by the AI router to pick a tier). ``profile`` pins the call
        to one configured provider (user's chosen AI); it still retries but
        does not fall back to other providers.
        """
        selected = self._select(profile)
        if selected is not None:
            return await self._complete_with_retry(
                selected, messages, system, tools, model
            )

        errors: list[str] = []
        for provider in self._chain():
            if not provider.is_available():
                errors.append(f"{provider.name}: no credentials")
                continue
            try:
                return await self._complete_with_retry(
                    provider, messages, system, tools, model
                )
            except LLMError as exc:
                logger.warning("Provider '%s' failed: %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
                continue

        raise AllProvidersFailedError(
            "All LLM providers failed or are unconfigured.",
            details={"errors": errors},
        )

    async def _complete_with_retry(
        self,
        provider: LLMProvider,
        messages: list[dict],
        system: str | None,
        tools: list[ToolSpec] | None,
        model: str | None = None,
    ) -> LLMResult:
        @retry_async(attempts=self._retry_attempts, base_delay=1.0, exceptions=(LLMError,))
        async def _call() -> LLMResult:
            return await provider.complete(messages, system, tools, model)

        return await _call()

    # -- streaming ----------------------------------------------------------

    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
        profile: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a completion, falling back before the first chunk only.

        Once a provider has produced its first chunk we are committed to it;
        mid-stream fallback is not possible. ``profile`` pins the stream to one
        configured provider (the user's chosen AI).
        """
        selected = self._select(profile)
        if selected is not None:
            async for chunk in selected.stream(messages, system):
                yield chunk
            return

        errors: list[str] = []
        for provider in self._chain():
            if not provider.is_available():
                errors.append(f"{provider.name}: no credentials")
                continue
            agen = provider.stream(messages, system)
            try:
                first = await agen.__anext__()
            except StopAsyncIteration:
                return  # empty but successful stream
            except LLMError as exc:
                logger.warning("Provider '%s' stream failed: %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
                continue

            yield first
            async for chunk in agen:
                yield chunk
            return

        raise AllProvidersFailedError(
            "All LLM providers failed or are unconfigured.",
            details={"errors": errors},
        )

    # -- tool-loop helpers --------------------------------------------------

    def continuation_messages(
        self,
        result: LLMResult,
        tool_results: list[ToolResult],
    ) -> list[dict]:
        """Format tool-round follow-up messages using the producing provider."""
        provider = self._provider_by_name(result.provider) or self.primary
        return provider.continuation_messages(result, tool_results)

    def _provider_by_name(self, name: str) -> LLMProvider | None:
        for provider in self._chain():
            if provider.name == name:
                return provider
        return None

    # -- introspection ------------------------------------------------------

    def _chain(self) -> list[LLMProvider]:
        return [self.primary, *self.fallbacks]

    def available_providers(self) -> list[str]:
        return [p.name for p in self._chain() if p.is_available()]

    def has_any_provider(self) -> bool:
        return bool(self.available_providers())
