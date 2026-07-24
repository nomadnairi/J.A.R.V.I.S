"""OpenAI (GPT) provider implementation — async, with tools & streaming."""

from __future__ import annotations

import json
from typing import AsyncIterator

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.tools import ToolCall, ToolResult, ToolSpec
from jarvis.utils.exceptions import LLMConfigError, LLMRequestError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

#: OpenRouter API keys use this prefix; the base URL of its OpenAI-compatible API.
_OPENROUTER_PREFIX = "sk-or-"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def _effective_base_url(self) -> str | None:
        """Resolve the base URL, catching a common misconfiguration.

        An OpenRouter key (``sk-or-*``) sent to the default OpenAI endpoint
        always fails with 401, so when no base URL is configured but the key is
        clearly an OpenRouter key, route to OpenRouter instead of guaranteeing a
        failure — and say so, so the fix (setting OPENAI_BASE_URL) is obvious.
        """
        if self.base_url:
            return self.base_url
        if (self.api_key or "").startswith(_OPENROUTER_PREFIX):
            logger.warning(
                "OPENAI_API_KEY looks like an OpenRouter key (sk-or-*) but "
                "OPENAI_BASE_URL is not set — routing to %s. Set "
                "OPENAI_BASE_URL=%s to make this explicit.",
                _OPENROUTER_BASE_URL, _OPENROUTER_BASE_URL)
            return _OPENROUTER_BASE_URL
        return None

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMConfigError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc
        # base_url lets this provider target any OpenAI-compatible gateway
        # (OpenRouter, Together, a local proxy, …) with the same code path.
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self._effective_base_url(),
        )
        return self._client

    @staticmethod
    def _with_system(messages: list[dict], system: str | None) -> list[dict]:
        if not system:
            return messages
        return [{"role": "system", "content": system}, *messages]

    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMConfigError("Missing OpenAI API key.")

        client = self._ensure_client()
        use_model = model or self.model
        kwargs: dict = {
            "model": use_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": self._with_system(messages, system),
        }
        if tools:
            kwargs["tools"] = [t.to_openai() for t in tools]

        try:
            response = await client.chat.completions.create(**kwargs)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise LLMRequestError(
                f"OpenAI request failed: {exc}",
                details={"model": use_model},
            ) from exc

        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        for call in getattr(message, "tool_calls", None) or []:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=call.id, name=call.function.name, arguments=args))

        usage = getattr(response, "usage", None)
        return LLMResult(
            text=(message.content or "").strip(),
            model=use_model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "",
            raw=response,
        )

    async def stream(
        self,
        messages: list[dict],
        system: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise LLMConfigError("Missing OpenAI API key.")

        client = self._ensure_client()
        use_model = model or self.model
        try:
            stream = await client.chat.completions.create(  # type: ignore[attr-defined]
                model=use_model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=self._with_system(messages, system),
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001
            raise LLMRequestError(
                f"OpenAI stream failed: {exc}",
                details={"model": use_model},
            ) from exc

    def continuation_messages(
        self,
        result: LLMResult,
        tool_results: list[ToolResult],
    ) -> list[dict]:
        assistant_msg = {
            "role": "assistant",
            "content": result.text or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in result.tool_calls
            ],
        }
        tool_msgs = [
            {"role": "tool", "tool_call_id": tr.call_id, "content": tr.content}
            for tr in tool_results
        ]
        return [assistant_msg, *tool_msgs]
