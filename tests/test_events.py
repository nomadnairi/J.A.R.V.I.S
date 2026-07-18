"""Tests for the async event bus."""

from __future__ import annotations

import pytest

from jarvis.config.constants import EventType
from jarvis.events.bus import EventBus
from jarvis.events.events import Event


@pytest.mark.asyncio
async def test_publish_reaches_subscriber():
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(EventType.USER_INPUT, received.append)

    await bus.emit(EventType.USER_INPUT, source="test", text="hello")

    assert len(received) == 1
    assert received[0].get("text") == "hello"


@pytest.mark.asyncio
async def test_async_handler_is_awaited():
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(str(event.get("text")))

    bus.subscribe(EventType.USER_INPUT, handler)
    await bus.emit(EventType.USER_INPUT, text="async!")
    assert received == ["async!"]


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received: list[Event] = []
    unsub = bus.subscribe(EventType.ERROR, received.append)
    unsub()
    await bus.emit(EventType.ERROR, source="test")
    assert received == []


@pytest.mark.asyncio
async def test_wildcard_receives_everything():
    bus = EventBus()
    seen: list[EventType] = []
    bus.subscribe_all(lambda e: seen.append(e.type))
    await bus.emit(EventType.STARTUP)
    await bus.emit(EventType.SHUTDOWN)
    assert seen == [EventType.STARTUP, EventType.SHUTDOWN]


@pytest.mark.asyncio
async def test_handler_error_is_isolated():
    bus = EventBus()
    calls: list[int] = []

    def bad(_):
        raise RuntimeError("boom")

    bus.subscribe(EventType.USER_INPUT, bad)
    bus.subscribe(EventType.USER_INPUT, lambda _: calls.append(1))

    # Should not raise despite the bad handler.
    await bus.emit(EventType.USER_INPUT)
    assert calls == [1]
