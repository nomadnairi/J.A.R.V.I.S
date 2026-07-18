"""
Integrations subsystem (contracts).

Stage 1 defines the abstract interface only. Stage 4 will add concrete
connectors: smart home, calendar, email, media, and custom webhooks.
"""

from jarvis.integrations.base import BaseIntegration, IntegrationStatus

__all__ = ["BaseIntegration", "IntegrationStatus"]
