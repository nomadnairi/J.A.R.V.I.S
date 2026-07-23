"""
MCP (Model Context Protocol) core types.

MCP is the open standard — used by the agentskills.io ecosystem, Hermes Agent,
Claude and others — for exposing tools/skills from a separate process or service.
J.A.R.V.I.S. is an MCP *client*: it connects to configured MCP servers, discovers
their tools and mounts each one as a native skill (see :mod:`jarvis.mcp.skill`).

These types are transport-agnostic and dependency-free so the discovery and
tool-wrapping logic is unit-testable without a live server or the `mcp` SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MCPServerConfig:
    """How to reach one MCP server (stdio subprocess or an HTTP/SSE endpoint)."""

    name: str
    transport: str = "stdio"          # "stdio" | "sse"
    command: str = ""                 # stdio: executable
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""                     # sse: endpoint URL

    @classmethod
    def from_spec(cls, name: str, spec: dict) -> "MCPServerConfig":
        """Parse one entry of a standard ``{"mcpServers": {...}}`` config."""
        url = spec.get("url", "")
        transport = spec.get("transport") or ("sse" if url else "stdio")
        return cls(
            name=name,
            transport=transport,
            command=spec.get("command", ""),
            args=list(spec.get("args", []) or []),
            env=dict(spec.get("env", {}) or {}),
            url=url,
        )

    def is_valid(self) -> bool:
        if self.transport == "stdio":
            return bool(self.command)
        if self.transport == "sse":
            return self.url.startswith("http")
        return False


@dataclass(frozen=True)
class MCPTool:
    """A tool advertised by an MCP server."""

    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


class MCPSession(ABC):
    """A live connection to one MCP server."""

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """Discover the server's tools."""
        raise NotImplementedError

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> str:
        """Invoke ``name`` with ``arguments`` and return a text result."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release the connection (subprocess / socket). Optional."""
        return None
