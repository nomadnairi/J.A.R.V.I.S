"""Event objects published on the :class:`~jarvis.events.bus.EventBus`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from jarvis.config.constants import EventType


@dataclass
class Event:
    """An immutable notification that something happened.

    Attributes:
        type: The :class:`EventType` categorising the event.
        payload: Arbitrary event data (kept as a plain dict for flexibility).
        source: Which component emitted the event.
        timestamp: When the event was created (UTC).
    """

    type: EventType
    payload: dict = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get(self, key: str, default: object = None) -> object:
        """Convenience accessor for ``payload``."""
        return self.payload.get(key, default)
