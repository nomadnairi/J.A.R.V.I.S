"""
Unified LLM client.

Wraps one or more :class:`~jarvis.llm.base.LLMProvider` instances behind a
single ``complete`` call, adding:

* automatic retry with exponential backoff (transient failures), and
* provider fallback — if the primary provider fails, configured fallbacks are
  tried in order before giving up.

The rest of the system talks only to this class.
"""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.providers import PROVIDER_REGISTRY
from jarvis.utils.exceptions import (
    AllProvidersFailedError,
    LLMConfigError,
    LLMError,
)
from jarvis.utils.logger import get_logger
from jarvis.utils.retry import retry

logger = get_logger(__name__)


class LLMClient:
    """Provider-agnostic client with retry and fallback."""

    def __init__(
        self,
        primary: LLMProvider,
        fallbacks: list[LLMProvider] | None = None,
        *,
        retry_attempts: int = 3,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks or []
        self._retry_attempts = retry_attempts

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

        return cls(primary, fallbacks)

    @staticmethod
    def _make_provider(settings: Settings, name: str,
                    model: str | None = None) -> LLMProvider:
        provider_cls = PROVIDER_REGISTRY.get(name)
        if provider_cls is None:
            raise LLMConfigError(f"Unknown LLM provider: {name!r}")

        from jarvis.config.constants import DEFAULT_MODELS
        key = (settings.anthropic_api_key if name == "anthropic"
            else settings.openai_api_key)
        return provider_cls(
            api_key=key,
            model=model or DEFAULT_MODELS.get(name, ""),
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    # -- completion ---------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
    ) -> LLMResult:
        """Complete ``messages``, retrying and falling back as needed."""
        chain = [self.primary, *self.fallbacks]
        errors: list[str] = []

        for provider in chain:
            if not provider.is_available():
                errors.append(f"{provider.name}: no credentials")
                continue
            try:
                return self._complete_with_retry(provider, messages, system)
            except LLMError as exc:
                logger.warning("Provider '%s' failed: %s", provider.name, exc)
                errors.append(f"{provider.name}: {exc}")
                continue

        raise AllProvidersFailedError(
            "All LLM providers failed or are unconfigured.",
            details={"errors": errors},
        )

    def _complete_with_retry(
        self,
        provider: LLMProvider,
        messages: list[dict[str, str]],
        system: str | None,
    ) -> LLMResult:
        @retry(attempts=self._retry_attempts, base_delay=1.0, exceptions=(LLMError,))
        def _call() -> LLMResult:
            return provider.complete(messages, system)

        return _call()

    # -- introspection ------------------------------------------------------

    def available_providers(self) -> list[str]:
        return [p.name for p in [self.primary, *self.fallbacks] if p.is_available()]

    def has_any_provider(self) -> bool:
        return bool(self.available_providers())
