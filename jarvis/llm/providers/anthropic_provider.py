"""Anthropic (Claude) provider implementation."""

from __future__ import annotations

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.utils.exceptions import LLMConfigError, LLMRequestError


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API."""

    name = "anthropic"

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMConfigError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMConfigError("Missing Anthropic API key.")

        client = self._ensure_client()
        try:
            response = client.messages.create(  # type: ignore[attr-defined]
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system or "",
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMRequestError(
                f"Anthropic request failed: {exc}",
                details={"model": self.model},
            ) from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

        usage = getattr(response, "usage", None)
        return LLMResult(
            text=text,
            model=self.model,
            provider=self.name,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            raw=response,
        )
