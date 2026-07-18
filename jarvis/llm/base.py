"""
Abstract LLM provider contract.

Concrete providers (Anthropic, OpenAI, and future local models) implement
:class:`LLMProvider`. The rest of the system depends only on this interface,
never on a vendor SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    """Normalised result returned by every provider."""

    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: object = field(default=None, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    #: Provider identifier, e.g. ``"anthropic"``.
    name: str = "base"

    def __init__(self, api_key: str, model: str, *, temperature: float = 0.7,
                max_tokens: int = 2048) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: object | None = None

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
    ) -> LLMResult:
        """Generate a completion for ``messages`` with an optional system prompt.

        Args:
            messages: Ordered ``{role, content}`` dicts (roles: user/assistant).
            system: Optional system prompt.

        Returns:
            A populated :class:`LLMResult`.

        Raises:
            LLMError (or subclass) on failure.
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Whether the provider has the credentials it needs to run."""
        return bool(self.api_key)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<{type(self).__name__} model={self.model!r}>"
