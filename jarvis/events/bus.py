"""
A synchronous publish/subscribe event bus.

Components subscribe handlers to :class:`EventType` values and publish
:class:`Event` objects without knowing about each other. This keeps the core
engine decoupled from cross-cutting concerns like telemetry, logging, and
(later) the UI layer.

The bus is intentionally synchronous and dependency-free — handler errors are
isolated so one bad subscriber never breaks publishing.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from jarvis.config.constants import EventType
from jarvis.events.events import Event
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

Handler = Callable[[Event], None]


class EventBus:
    """A simple, robust in-process event bus."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    # -- subscription -------------------------------------------------------

    def subscribe(self, event_type: EventType, handler: Handler) -> Callable[[], None]:
        """Register ``handler`` for ``event_type``.

        Returns an unsubscribe callable.
        """
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", getattr(handler, "__name__", handler), event_type)

        def _unsubscribe() -> None:
            self.unsubscribe(event_type, handler)

        return _unsubscribe

    def subscribe_all(self, handler: Handler) -> Callable[[], None]:
        """Register a handler that receives *every* event."""
        self._wildcard.append(handler)

        def _unsubscribe() -> None:
            if handler in self._wildcard:
                self._wildcard.remove(handler)

        return _unsubscribe

    def unsubscribe(self, event_type: EventType, handler: Handler) -> None:
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    # -- publishing ---------------------------------------------------------

    def publish(self, event: Event) -> None:
        """Dispatch ``event`` to all matching handlers.

        Handler exceptions are caught and logged so a single failing
        subscriber cannot disrupt the others or the publisher.
        """
        handlers = list(self._handlers.get(event.type, [])) + list(self._wildcard)
        if not handlers:
            return
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - isolate subscriber failures
                logger.exception(
                    "Event handler %s failed for %s",
                    getattr(handler, "__name__", handler),
                    event.type,
                )

    def emit(self, event_type: EventType, source: str = "", **payload: object) -> None:
        """Shorthand for constructing and publishing an :class:`Event`."""
        self.publish(Event(type=event_type, source=source, payload=dict(payload)))

    # -- introspection ------------------------------------------------------

    def handler_count(self, event_type: EventType | None = None) -> int:
        """Number of registered handlers (for a type, or in total)."""
        if event_type is not None:
            return len(self._handlers.get(event_type, []))
        return sum(len(h) for h in self._handlers.values()) + len(self._wildcard)

    def clear(self) -> None:
        self._handlers.clear()
        self._wildcard.clear()
