"""
Request / Response envelopes that flow through the processing pipeline.

Keeping input and output in structured objects (rather than bare strings)
lets middleware, skills, and telemetry attach metadata as a turn is handled.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from jarvis.config.constants import ResponseType


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Request:
    """A single inbound user request as it enters the pipeline."""

    text: str
    request_id: str = field(default_factory=_uuid)
    session_id: str = "default"
    source: str = "cli"          # cli | api | voice | ...
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


@dataclass
class Response:
    """The assistant's answer to a :class:`Request`."""

    text: str
    request_id: str = ""
    type: ResponseType = ResponseType.LLM
    source: str = ""             # which skill/provider produced it
    latency_ms: float = 0.0
    tokens: int = 0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_skill(cls, text: str, skill_name: str, **kw: object) -> "Response":
        return cls(text=text, type=ResponseType.SKILL, source=skill_name, **kw)

    @classmethod
    def from_llm(cls, text: str, provider: str, **kw: object) -> "Response":
        return cls(text=text, type=ResponseType.LLM, source=provider, **kw)

    @classmethod
    def system_message(cls, text: str, **kw: object) -> "Response":
        return cls(text=text, type=ResponseType.SYSTEM, source="system", **kw)
