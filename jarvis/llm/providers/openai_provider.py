"""OpenAI (GPT) provider implementation."""

from __future__ import annotations

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.utils.exceptions import LLMConfigError, LLMRequestError


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMConfigError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMConfigError("Missing OpenAI API key.")

        client = self._ensure_client()

        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(messages)

        try:
            response = client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=payload,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMRequestError(
                f"OpenAI request failed: {exc}",
                details={"model": self.model},
            ) from exc

        text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        return LLMResult(
            text=text,
            model=self.model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            raw=response,
        )
