"""
Weather integration (Open-Meteo).

Uses the free, key-less Open-Meteo API for geocoding and current weather, so it
works out of the box. Exposes a ``get_weather`` tool the assistant can call.
"""

from __future__ import annotations

from jarvis.integrations.base import (
    BaseIntegration,
    IntegrationAction,
    IntegrationStatus,
)
from jarvis.integrations.http import HttpClient

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# A readable label for the most common WMO weather codes.
_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


class WeatherIntegration(BaseIntegration):
    """Current weather for a location via Open-Meteo (no API key needed)."""

    name = "weather"
    description = "Current weather for any location (Open-Meteo, no key)."

    def __init__(self, enabled: bool = True, http: HttpClient | None = None) -> None:
        super().__init__()
        self._enabled = enabled
        self._http = http or HttpClient()

    def is_configured(self) -> bool:
        return self._enabled

    async def connect(self) -> IntegrationStatus:
        # Stateless public API — nothing to authenticate.
        return self._mark_connected("ready")

    def actions(self) -> list[IntegrationAction]:
        return [
            IntegrationAction(
                name="get_weather",
                description=(
                    "Get the current weather for a place (city, town, or region). "
                    "Provide the location name."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Place name, e.g. 'Tashkent' or 'Berlin'.",
                        }
                    },
                    "required": ["location"],
                },
                handler=self.get_weather,
            )
        ]

    async def get_weather(self, location: str = "", **_: object) -> str:
        location = (location or "").strip()
        if not location:
            return "Please tell me which location you want the weather for."

        geo = await self._http.get_json(
            _GEOCODE_URL, params={"name": location, "count": 1}
        )
        results = geo.get("results") or []
        if not results:
            return f"I couldn't find a place called '{location}'."
        place = results[0]

        forecast = await self._http.get_json(
            _FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
            },
        )
        current = forecast.get("current") or {}
        temp = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        condition = _WMO.get(int(current.get("weather_code", -1)), "unknown conditions")

        name = place.get("name", location)
        country = place.get("country", "")
        where = f"{name}, {country}".rstrip(", ")
        return f"{where}: {condition}, {temp}°C, wind {wind} km/h."

    async def current(self, location: str) -> dict | None:
        """Structured current weather for ``location`` (for dashboards)."""
        location = (location or "").strip()
        if not location:
            return None
        geo = await self._http.get_json(_GEOCODE_URL,
                                        params={"name": location, "count": 1})
        results = geo.get("results") or []
        if not results:
            return None
        place = results[0]
        forecast = await self._http.get_json(
            _FORECAST_URL,
            params={"latitude": place["latitude"], "longitude": place["longitude"],
                    "current": "temperature_2m,weather_code,wind_speed_10m"})
        cur = forecast.get("current") or {}
        code = int(cur.get("weather_code", -1))
        name = place.get("name", location)
        country = place.get("country", "")
        return {
            "temp": f"{round(float(cur.get('temperature_2m', 0)))}°",
            "loc": f"{name}, {country}".rstrip(", "),
            "cond": _WMO.get(code, "—"),
            "wind": cur.get("wind_speed_10m"),
            "glyph": _weather_glyph(code),
        }


def _weather_glyph(code: int) -> str:
    if code == 0:
        return "☀️"
    if code in (1, 2):
        return "🌤"
    if code == 3:
        return "☁️"
    if code in (45, 48):
        return "🌫"
    if 51 <= code <= 67:
        return "🌧"
    if 71 <= code <= 77:
        return "❄️"
    if 80 <= code <= 82:
        return "🌦"
    if code >= 95:
        return "⛈"
    return "🛰"
