"""
Local / self-hosted model provider.

Ollama, LM Studio, vLLM and llama.cpp all expose an OpenAI-compatible Chat
Completions endpoint, so this provider reuses the OpenAI request path and only
swaps the base URL for the chosen backend's preset. No cloud key is required —
these servers usually ignore auth — so a placeholder token is used unless
``LOCAL_LLM_API_KEY`` is set.
"""

from __future__ import annotations

from jarvis.llm.providers.openai_provider import OpenAIProvider

#: Default OpenAI-compatible endpoint for each supported local backend.
LOCAL_BACKENDS: dict[str, str] = {
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
    "vllm": "http://localhost:8000/v1",
    "llamacpp": "http://localhost:8080/v1",
}

#: Sent as the API key when the user hasn't set one (local servers ignore it).
_PLACEHOLDER_KEY = "local"


class LocalProvider(OpenAIProvider):
    """A local model server reached over the OpenAI-compatible protocol."""

    name = "local"

    def __init__(self, api_key: str, model: str, *, temperature: float = 0.7,
                max_tokens: int = 2048, base_url: str = "",
                backend: str = "ollama") -> None:
        # Local endpoints accept any token; keep the call path happy with a
        # placeholder when none is provided.
        super().__init__(api_key or _PLACEHOLDER_KEY, model,
                        temperature=temperature, max_tokens=max_tokens,
                        base_url=base_url)
        self.backend = backend if backend in LOCAL_BACKENDS or backend == "custom" \
            else "ollama"

    def _effective_base_url(self) -> str | None:
        # An explicit base_url always wins (required for the "custom" backend);
        # otherwise use the preset for the selected backend.
        if self.base_url:
            return self.base_url
        return LOCAL_BACKENDS.get(self.backend, LOCAL_BACKENDS["ollama"])

    def is_available(self) -> bool:
        # No cloud credentials needed — a configured model + reachable endpoint
        # is enough. We can't ping here, so treat a set model as available.
        return bool(self.model) and self._effective_base_url() is not None
