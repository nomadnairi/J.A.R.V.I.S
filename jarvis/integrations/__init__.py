"""
Integrations subsystem (contracts).

Defines the abstract interface for third-party connectors. Concrete
connectors (smart home, calendar, email, media, custom webhooks) build on it.
"""

from jarvis.integrations.base import BaseIntegration, IntegrationStatus

__all__ = ["BaseIntegration", "IntegrationStatus"]
