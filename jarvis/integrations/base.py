"""
Abstract integration contract.

Every third-party connector (smart home, calendar, email, ...) implements
:class:`BaseIntegration`. Defining the contract keeps the engine and skill
layers stable as connectors are added.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class IntegrationState(str, Enum):
    """Connection state of an integration."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class IntegrationStatus:
    """Health snapshot of an integration."""

    name: str
    state: IntegrationState = IntegrationState.DISCONNECTED
    detail: str = ""


class BaseIntegration(ABC):
    """Interface for external service connectors."""

    #: Unique integration name.
    name: str = "base"

    @abstractmethod
    def connect(self) -> IntegrationStatus:
        """Establish a connection to the external service."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection."""
        raise NotImplementedError

    @abstractmethod
    def status(self) -> IntegrationStatus:
        """Return the current health/connection status."""
        raise NotImplementedError
