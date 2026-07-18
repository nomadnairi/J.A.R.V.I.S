"""
Conversation primitives: :class:`Message` and :class:`Conversation`.

These are deliberately provider-agnostic — the LLM layer converts them into
whatever shape a given SDK expects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from jarvis.config.constants import Role


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Message:
    """A single conversation turn."""

    role: Role
    content: str
    timestamp: datetime = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, str]:
        """Minimal provider-friendly representation."""
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def user(cls, content: str, **meta: object) -> "Message":
        return cls(role=Role.USER, content=content, metadata=dict(meta))

    @classmethod
    def assistant(cls, content: str, **meta: object) -> "Message":
        return cls(role=Role.ASSISTANT, content=content, metadata=dict(meta))

    @classmethod
    def system(cls, content: str, **meta: object) -> "Message":
        return cls(role=Role.SYSTEM, content=content, metadata=dict(meta))


@dataclass
class Conversation:
    """An ordered, size-bounded history of messages.

    ``max_turns`` limits how many *messages* are retained for the LLM context
    window; older turns are trimmed from the front (the system prompt is kept
    separately by the engine, not stored here).
    """

    messages: list[Message] = field(default_factory=list)
    max_turns: int = 40

    def add(self, message: Message) -> None:
        self.messages.append(message)
        self._trim()

    def add_user(self, content: str, **meta: object) -> Message:
        msg = Message.user(content, **meta)
        self.add(msg)
        return msg

    def add_assistant(self, content: str, **meta: object) -> Message:
        msg = Message.assistant(content, **meta)
        self.add(msg)
        return msg

    def _trim(self) -> None:
        if len(self.messages) > self.max_turns:
            self.messages = self.messages[-self.max_turns:]

    def to_provider_format(self) -> list[dict[str, str]]:
        """Return messages as a list of ``{role, content}`` dicts."""
        return [m.as_dict() for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.messages)
