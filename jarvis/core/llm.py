"""
LLM abstraction layer.

Wraps the underlying provider SDKs (Anthropic / OpenAI) behind a single
:class:`LLMClient` interface so the rest of J.A.R.V.I.S. never talks to a
vendor SDK directly. Swapping models or providers is a config change, not a
code change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

Role = Literal["user", "assistant"]


class LLMError(RuntimeError):
    """Raised when the underlying LLM provider fails or is misconfigured."""


@dataclass
class Message:
    """A single turn in a conversation."""

    role: Role
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMClient:
    """Provider-agnostic chat client.

    The client is created lazily: the provider SDK is only imported and
    instantiated on first use, so importing this module never requires the
    vendor packages to be installed unless you actually make a call.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = settings.llm_provider
        self._client: object | None = None

        if not settings.has_llm_credentials():
            logger.warning(
                "No API key configured for provider '%s'. "
                "Set the relevant key in your .env file.",
                self._provider,
            )

    # -- public API ---------------------------------------------------------

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
    ) -> str:
        """Send a conversation and return the assistant's reply text.

        Args:
            messages: Ordered conversation turns (user/assistant).
            system: Optional system prompt establishing persona / rules.

        Raises:
            LLMError: If credentials are missing or the provider call fails.
        """
        if not self._settings.has_llm_credentials():
            raise LLMError(
                f"Missing API key for provider '{self._provider}'. "
                "Add it to your .env file."
            )

        if self._provider == "anthropic":
            return self._chat_anthropic(messages, system)
        if self._provider == "openai":
            return self._chat_openai(messages, system)
        raise LLMError(f"Unknown LLM provider: {self._provider!r}")

    # -- provider implementations ------------------------------------------

    def _chat_anthropic(self, messages: list[Message], system: str | None) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=self._settings.anthropic_api_key
            )

        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=self._settings.llm_model,
                max_tokens=self._settings.llm_max_tokens,
                temperature=self._settings.llm_temperature,
                system=system or "",
                messages=[m.as_dict() for m in messages],
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK error uniformly
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

    def _chat_openai(self, messages: list[Message], system: str | None) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc

        if self._client is None:
            self._client = OpenAI(api_key=self._settings.openai_api_key)

        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(m.as_dict() for m in messages)

        try:
            response = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._settings.llm_model,
                max_tokens=self._settings.llm_max_tokens,
                temperature=self._settings.llm_temperature,
                messages=payload,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        return (response.choices[0].message.content or "").strip()
