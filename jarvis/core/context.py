"""
Session context.

A :class:`SessionContext` bundles everything tied to a single conversation
session: its id, the running conversation history, and a scratch dict for
per-session state (used later by memory and integrations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from jarvis.models.message import Conversation


@dataclass
class SessionContext:
    """State for one conversation session."""

    session_id: str = "default"
    conversation: Conversation = field(default_factory=Conversation)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scratch: dict = field(default_factory=dict)

    def turns(self) -> int:
        """Number of messages exchanged so far."""
        return len(self.conversation)

    def reset(self) -> None:
        """Clear the conversation but keep the session identity."""
        self.conversation.clear()
        self.scratch.clear()
