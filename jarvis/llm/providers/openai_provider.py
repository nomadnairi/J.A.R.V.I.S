"""OpenAI (GPT) provider implementation — async, with tools & streaming."""

from __future__ import annotations

import json
from typing import AsyncIterator

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.tools import ToolCall, ToolResult, ToolSpec
from jarvis.utils.exceptions import LLMConfigError, LLMRequestError


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise LLMConfigError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc
        self._client = AsyncOpenAI(api_key=self.api_key)
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
    ) -> LLMResult:
        if not self.api_key:
            raise LLMConfigError("Missing OpenAI API key.")

        client = self._ensure_client()
        kwargs: dict = {
            "model": self.model,
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
                details={"model": self.model},
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
            model=self.model,
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
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise LLMConfigError("Missing OpenAI API key.")

        client = self._ensure_client()
        try:
            stream = await client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.model,
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
                details={"model": self.model},
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
