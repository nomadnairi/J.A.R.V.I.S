"""Tests for the integrations subsystem (HTTP mocked — no network)."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.integrations.base import IntegrationState
from jarvis.integrations.homeassistant import HomeAssistantIntegration
from jarvis.integrations.manager import IntegrationManager
from jarvis.integrations.weather import WeatherIntegration
from jarvis.llm.client import LLMClient
from jarvis.models.response import Request
from jarvis.skills.registry import SkillRegistry
from tests.conftest import FakeProvider, make_tool_call_result


class FakeHttp:
    """A fake HttpClient returning queued responses by (method, url-substring)."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls: list[tuple[str, str]] = []

    async def _match(self, method: str, url: str):
        self.calls.append((method, url))
        for key, value in self.routes.items():
            m, frag = key
            if m == method and frag in url:
                return value
        return {}

    async def request_json(self, method, url, *, params=None, json=None, headers=None):
        return await self._match(method, url)

    async def get_json(self, url, *, params=None, headers=None):
        return await self._match("GET", url)

    async def post_json(self, url, *, json=None, headers=None):
        return await self._match("POST", url)


# -- weather ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_weather_get():
    http = FakeHttp({
        ("GET", "geocoding-api"): {
            "results": [{"latitude": 41.3, "longitude": 69.2, "name": "Tashkent",
                        "country": "Uzbekistan"}]
        },
        ("GET", "/v1/forecast"): {
            "current": {"temperature_2m": 24.5, "weather_code": 0, "wind_speed_10m": 8}
        },
    })
    weather = WeatherIntegration(http=http)
    result = await weather.get_weather("Tashkent")
    assert "Tashkent" in result and "24.5" in result and "clear sky" in result


@pytest.mark.asyncio
async def test_weather_unknown_place():
    http = FakeHttp({("GET", "geocoding-api"): {"results": []}})
    weather = WeatherIntegration(http=http)
    assert "couldn't find" in await weather.get_weather("Nowhereville")


def test_weather_is_configured():
    assert WeatherIntegration(enabled=True).is_configured() is True
    assert WeatherIntegration(enabled=False).is_configured() is False


# -- home assistant ---------------------------------------------------------


def test_homeassistant_requires_config():
    assert HomeAssistantIntegration("", "").is_configured() is False
    assert HomeAssistantIntegration("http://ha", "tok").is_configured() is True


@pytest.mark.asyncio
async def test_homeassistant_connect_and_turn_on():
    http = FakeHttp({
        ("GET", "/api/"): {"message": "API running."},
        ("POST", "/api/services/light/turn_on"): {},
    })
    ha = HomeAssistantIntegration("http://ha:8123", "token", http=http)
    status = await ha.connect()
    assert status.state == IntegrationState.CONNECTED
    result = await ha.turn_on("light.kitchen")
    assert "light.kitchen" in result
    assert ("POST", "http://ha:8123/api/services/light/turn_on") in http.calls


@pytest.mark.asyncio
async def test_homeassistant_turn_on_validates_entity():
    ha = HomeAssistantIntegration("http://ha", "token", http=FakeHttp({}))
    assert "valid entity" in await ha.turn_on("not-an-entity")


@pytest.mark.asyncio
async def test_homeassistant_rejects_path_traversal_entity():
    ha = HomeAssistantIntegration("http://ha", "token", http=FakeHttp({}))
    # A crafted id must not be able to escape the API path.
    assert "valid entity" in await ha.get_state("../../config")
    assert "valid entity" in await ha.turn_off("light.kitchen/../admin")


# -- manager + tool bridge --------------------------------------------------


def test_manager_installs_tools_only_for_configured():
    manager = IntegrationManager()
    manager.register(WeatherIntegration(enabled=True))
    manager.register(HomeAssistantIntegration("", ""))  # unconfigured
    registry = SkillRegistry()
    installed = manager.install_tools(registry)
    names = set(registry.names())
    assert "get_weather" in names
    assert not any(n.startswith("home_") for n in names)  # HA not configured
    assert installed == 1


@pytest.mark.asyncio
async def test_manager_connect_all():
    manager = IntegrationManager()
    manager.register(WeatherIntegration(enabled=True))
    statuses = await manager.connect_all()
    assert statuses[0].state == IntegrationState.CONNECTED


# -- engine end-to-end (LLM calls an integration tool) ----------------------


@pytest.mark.asyncio
async def test_engine_invokes_integration_tool():
    settings = Settings(anthropic_api_key="k", log_file="", memory_enabled=False,
                        integrations_enabled=True, weather_enabled=True)
    # First completion asks for the weather tool, second returns the final answer.
    provider = FakeProvider(
        default_reply="It's 24.5°C and clear in Tashkent.",
        results=[make_tool_call_result("get_weather", {"location": "Tashkent"})],
    )
    http = FakeHttp({
        ("GET", "geocoding-api"): {"results": [{"latitude": 41.3, "longitude": 69.2,
                                                "name": "Tashkent", "country": "UZ"}]},
        ("GET", "/v1/forecast"): {"current": {"temperature_2m": 24.5,
                                            "weather_code": 0, "wind_speed_10m": 8}},
    })
    manager = IntegrationManager()
    manager.register(WeatherIntegration(http=http))
    container = ServiceContainer(settings, llm_client=LLMClient(primary=provider),
                                integrations=manager)
    engine = JarvisEngine(container=container)

    response = await engine.process(Request(text="what's the weather in Tashkent?"))
    assert response.text == "It's 24.5°C and clear in Tashkent."
    assert len(provider.calls) == 2  # tool round + final answer
    assert ("GET", "https://geocoding-api.open-meteo.com/v1/search") in [
        (m, u) for m, u in http.calls
    ]
