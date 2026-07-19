"""
Integration contracts.

An *integration* connects J.A.R.V.I.S. to an external service (smart home,
weather, calendar, …). Each integration:

* has a lifecycle — :meth:`connect` / :meth:`disconnect` / :meth:`status`, and
* exposes one or more :class:`IntegrationAction` objects, which the manager
  bridges into the LLM tool system so the model can call them.

Concrete integrations subclass :class:`BaseIntegration`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable


class IntegrationState(str, Enum):
    """Connection state of an integration."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"


@dataclass
class IntegrationStatus:
    """Health snapshot of an integration."""

    name: str
    state: IntegrationState = IntegrationState.DISCONNECTED
    detail: str = ""


@dataclass
class IntegrationAction:
    """An action an integration exposes as an LLM-callable tool.

    Attributes:
        name: Unique tool name (namespaced, e.g. ``weather_get``).
        description: What the action does (the model reads this).
        parameters: JSON-Schema for the action's arguments.
        handler: Async callable invoked with the parsed arguments; returns a
            short text result fed back to the model.
    """

    name: str
    description: str
    parameters: dict
    handler: Callable[..., Awaitable[str]]


class BaseIntegration(ABC):
    """Base class for external-service connectors."""

    #: Unique integration name.
    name: str = "base"
    #: Human-readable description.
    description: str = ""

    def __init__(self) -> None:
        self._state = IntegrationState.DISCONNECTED
        self._detail = ""

    # -- configuration ------------------------------------------------------

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the integration has the config/credentials it needs."""
        raise NotImplementedError

    # -- lifecycle ----------------------------------------------------------

    @abstractmethod
    async def connect(self) -> IntegrationStatus:
        """Establish/verify the connection to the external service."""
        raise NotImplementedError

    async def disconnect(self) -> None:
        """Tear down the connection (override if resources are held)."""
        self._state = IntegrationState.DISCONNECTED

    def status(self) -> IntegrationStatus:
        """Return the current health/connection status."""
        if not self.is_configured():
            return IntegrationStatus(self.name, IntegrationState.UNCONFIGURED,
                                    "not configured")
        return IntegrationStatus(self.name, self._state, self._detail)

    # -- actions ------------------------------------------------------------

    @abstractmethod
    def actions(self) -> list[IntegrationAction]:
        """Return the actions this integration exposes as tools."""
        raise NotImplementedError

    # -- helpers ------------------------------------------------------------

    def _mark_connected(self, detail: str = "") -> IntegrationStatus:
        self._state, self._detail = IntegrationState.CONNECTED, detail
        return self.status()

    def _mark_error(self, detail: str) -> IntegrationStatus:
        self._state, self._detail = IntegrationState.ERROR, detail
        return self.status()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Integration {self.name!r} state={self._state.value}>"
