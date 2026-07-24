"""
MCP Manager — connects to configured MCP servers, discovers their tools and
mounts each as a J.A.R.V.I.S. skill.

Lifecycle mirrors the integrations layer: ``start()`` (called during
``engine.start()``) connects every server and returns the discovered skills to
register; ``stop()`` closes the sessions. A ``session_factory`` is injected so
discovery/wrapping is testable with a fake server; the default factory uses the
optional ``mcp`` SDK and is skipped gracefully when it isn't installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from jarvis.mcp.base import MCPServerConfig, MCPSession
from jarvis.mcp.skill import MCPToolSkill
from jarvis.skills.base import BaseSkill
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

SessionFactory = Callable[[MCPServerConfig], Awaitable[MCPSession]]


@dataclass
class ServerStatus:
    """Connection outcome for one MCP server."""

    name: str
    connected: bool
    tool_count: int = 0
    detail: str = ""


class MCPManager:
    """Owns MCP sessions and turns their tools into skills."""

    def __init__(self, servers: list[MCPServerConfig],
                session_factory: SessionFactory | None = None) -> None:
        self.servers = servers
        self._factory = session_factory or _default_session_factory
        self._sessions: list[MCPSession] = []
        self._statuses: list[ServerStatus] = []

    async def start(self) -> list[BaseSkill]:
        """Connect every server and return the skills to register."""
        skills: list[BaseSkill] = []
        for cfg in self.servers:
            try:
                session = await self._factory(cfg)
            except Exception as exc:  # noqa: BLE001 - one bad server mustn't stop others
                logger.warning("MCP server %r failed to connect: %s", cfg.name, exc)
                self._statuses.append(ServerStatus(cfg.name, False, detail=str(exc)))
                continue
            try:
                tools = await session.list_tools()
            except Exception as exc:  # noqa: BLE001
                logger.warning("MCP server %r tool discovery failed: %s",
                            cfg.name, exc)
                self._statuses.append(ServerStatus(cfg.name, False, detail=str(exc)))
                await _safe_close(session)
                continue
            self._sessions.append(session)
            for tool in tools:
                skills.append(MCPToolSkill(session, tool, cfg.name))
            self._statuses.append(ServerStatus(cfg.name, True, tool_count=len(tools)))
            logger.info("MCP server %r connected: %d tool(s).", cfg.name, len(tools))
        return skills

    async def stop(self) -> None:
        for session in self._sessions:
            await _safe_close(session)
        self._sessions.clear()

    def statuses(self) -> list[ServerStatus]:
        return list(self._statuses)


async def _safe_close(session: MCPSession) -> None:
    try:
        await session.close()
    except Exception as exc:  # noqa: BLE001
        logger.debug("MCP session close error: %s", exc)


async def _default_session_factory(cfg: MCPServerConfig) -> MCPSession:  # pragma: no cover - needs the SDK + a live server
    """Build a real MCP session using the optional ``mcp`` SDK."""
    try:
        from jarvis.mcp.sdk_session import connect
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "The 'mcp' package is required for MCP servers. "
            "Install it: pip install mcp") from exc
    return await connect(cfg)
