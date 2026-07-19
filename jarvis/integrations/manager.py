"""
Integration manager.

Registers integrations, connects the configured ones, tracks their health, and
installs their actions as tools in the skill registry.
"""

from __future__ import annotations

from jarvis.integrations.base import BaseIntegration, IntegrationStatus
from jarvis.integrations.tool_adapter import IntegrationToolSkill
from jarvis.skills.registry import SkillRegistry
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class IntegrationManager:
    """Manages the lifecycle of external-service integrations."""

    def __init__(self) -> None:
        self._integrations: list[BaseIntegration] = []

    # -- registration -------------------------------------------------------

    def register(self, integration: BaseIntegration) -> None:
        self._integrations.append(integration)
        logger.debug("Registered integration %r", integration.name)

    def register_many(self, integrations: list[BaseIntegration]) -> None:
        for integration in integrations:
            self.register(integration)

    # -- tool installation --------------------------------------------------

    def install_tools(self, registry: SkillRegistry) -> int:
        """Expose configured integrations' actions as tools. Returns the count."""
        installed = 0
        for integration in self._integrations:
            if not integration.is_configured():
                continue
            for action in integration.actions():
                try:
                    registry.register(IntegrationToolSkill(action))
                    installed += 1
                except Exception:  # noqa: BLE001 - skip duplicates/bad actions
                    logger.exception("Failed to install tool %r", action.name)
        logger.debug("Installed %d integration tool(s)", installed)
        return installed

    # -- lifecycle ----------------------------------------------------------

    async def connect_all(self) -> list[IntegrationStatus]:
        """Connect every configured integration; return their statuses."""
        statuses: list[IntegrationStatus] = []
        for integration in self._integrations:
            if not integration.is_configured():
                continue
            try:
                status = await integration.connect()
            except Exception as exc:  # noqa: BLE001 - one bad integration must not break others
                logger.warning("Integration %r failed to connect: %s",
                            integration.name, exc)
                status = integration.status()
            statuses.append(status)
            logger.info("Integration %r: %s", integration.name, status.state.value)
        return statuses

    async def disconnect_all(self) -> None:
        for integration in self._integrations:
            try:
                await integration.disconnect()
            except Exception:  # noqa: BLE001
                logger.exception("Error disconnecting %r", integration.name)

    # -- introspection ------------------------------------------------------

    def statuses(self) -> list[IntegrationStatus]:
        return [i.status() for i in self._integrations]

    def all(self) -> list[BaseIntegration]:
        return list(self._integrations)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._integrations)
