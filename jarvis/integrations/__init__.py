"""
Integrations subsystem.

Connects J.A.R.V.I.S. to external services and exposes their actions as tools
the LLM can call:

    IntegrationManager        — lifecycle + tool installation.
    WeatherIntegration        — current weather (Open-Meteo, free, no key).
    HomeAssistantIntegration  — smart-home control via Home Assistant.

All integrations implement :class:`BaseIntegration`.
"""

from jarvis.integrations.base import (
    BaseIntegration,
    IntegrationAction,
    IntegrationState,
    IntegrationStatus,
)
from jarvis.integrations.homeassistant import HomeAssistantIntegration
from jarvis.integrations.manager import IntegrationManager
from jarvis.integrations.weather import WeatherIntegration

__all__ = [
    "IntegrationManager",
    "BaseIntegration",
    "IntegrationAction",
    "IntegrationStatus",
    "IntegrationState",
    "WeatherIntegration",
    "HomeAssistantIntegration",
]
