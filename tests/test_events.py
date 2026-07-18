"""Tests for the event bus."""

from __future__ import annotations

from jarvis.config.constants import EventType
from jarvis.events.bus import EventBus
from jarvis.events.events import Event


def test_publish_reaches_subscriber():
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(EventType.USER_INPUT, received.append)

    bus.emit(EventType.USER_INPUT, source="test", text="hello")

    assert len(received) == 1
    assert received[0].get("text") == "hello"


def test_unsubscribe():
    bus = EventBus()
    received: list[Event] = []
    unsub = bus.subscribe(EventType.ERROR, received.append)
    unsub()
    bus.emit(EventType.ERROR, source="test")
    assert received == []


def test_wildcard_receives_everything():
    bus = EventBus()
    seen: list[EventType] = []
    bus.subscribe_all(lambda e: seen.append(e.type))
    bus.emit(EventType.STARTUP)
    bus.emit(EventType.SHUTDOWN)
    assert seen == [EventType.STARTUP, EventType.SHUTDOWN]


def test_handler_error_is_isolated():
    bus = EventBus()
    calls: list[int] = []

    def bad(_):
        raise RuntimeError("boom")

    bus.subscribe(EventType.USER_INPUT, bad)
    bus.subscribe(EventType.USER_INPUT, lambda _: calls.append(1))

    # Should not raise despite the bad handler.
    bus.emit(EventType.USER_INPUT)
    assert calls == [1]
