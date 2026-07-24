"""Tests for real dashboard data: conversation history + structured weather."""

from __future__ import annotations

import pytest

from jarvis.integrations.weather import WeatherIntegration, _weather_glyph
from jarvis.memory.conversation_store import SQLiteConversationStore
from jarvis.models.message import Message


# -- conversation history -----------------------------------------------------


def test_recent_sessions_titled_and_ordered():
    store = SQLiteConversationStore(":memory:")
    store.append("s1", Message.user("Помоги с Python"))
    store.append("s1", Message.assistant("Конечно"))
    store.append("s2", Message.user("Переведи текст"))
    rows = store.recent(10)
    by_id = {r["session_id"]: r for r in rows}
    assert by_id["s1"]["title"] == "Помоги с Python"
    assert by_id["s1"]["count"] == 2
    # Newest session first (s2 appended last).
    assert rows[0]["session_id"] == "s2"


def test_recent_empty_store():
    assert SQLiteConversationStore(":memory:").recent() == []


# -- weather ------------------------------------------------------------------


def test_weather_glyphs():
    assert _weather_glyph(0) == "☀️"
    assert _weather_glyph(3) == "☁️"
    assert _weather_glyph(65) == "🌧"
    assert _weather_glyph(95) == "⛈"


@pytest.mark.asyncio
async def test_weather_current_structured():
    class FakeHttp:
        async def get_json(self, url, params=None):
            if "geocoding" in url:
                return {"results": [{"name": "Tashkent", "country": "Uzbekistan",
                                    "latitude": 41.3, "longitude": 69.2}]}
            return {"current": {"temperature_2m": 24.6, "weather_code": 3,
                                "wind_speed_10m": 5.0}}

    wx = WeatherIntegration(http=FakeHttp())
    data = await wx.current("Tashkent")
    assert data["temp"] == "25°" and data["loc"] == "Tashkent, Uzbekistan"
    assert data["glyph"] == "☁️" and data["cond"] == "overcast"


@pytest.mark.asyncio
async def test_weather_current_unknown_place():
    class Empty:
        async def get_json(self, url, params=None):
            return {"results": []}
    assert await WeatherIntegration(http=Empty()).current("Nowhere") is None
