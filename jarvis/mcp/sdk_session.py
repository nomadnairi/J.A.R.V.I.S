"""
Real MCP session backed by the official ``mcp`` Python SDK.

Kept isolated (and out of unit tests) because it needs the optional SDK plus a
live server/subprocess. The manager imports :func:`connect` lazily, so the rest
of the MCP layer works — and is fully tested — without this dependency.
"""

from __future__ import annotations

from contextlib import AsyncExitStack

from jarvis.mcp.base import MCPServerConfig, MCPSession, MCPTool


class SDKSession(MCPSession):  # pragma: no cover - requires the mcp SDK + a server
    """Adapts an ``mcp.ClientSession`` to our :class:`MCPSession` interface."""

    def __init__(self, session, stack: AsyncExitStack) -> None:
        self._session = session
        self._stack = stack

    async def list_tools(self) -> list[MCPTool]:
        resp = await self._session.list_tools()
        return [MCPTool(name=t.name, description=t.description or "",
                        input_schema=getattr(t, "inputSchema", {}) or {})
                for t in resp.tools]

    async def call_tool(self, name: str, arguments: dict) -> str:
        result = await self._session.call_tool(name, arguments)
        parts: list[str] = []
        for item in getattr(result, "content", []) or []:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts) if parts else "(no output)"

    async def close(self) -> None:
        await self._stack.aclose()


async def connect(cfg: MCPServerConfig) -> MCPSession:  # pragma: no cover
    """Open a stdio or SSE MCP session for ``cfg`` and initialise it."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.stdio import StdioServerParameters, stdio_client

    stack = AsyncExitStack()
    if cfg.transport == "sse":
        read, write = await stack.enter_async_context(sse_client(cfg.url))
    else:
        params = StdioServerParameters(command=cfg.command, args=cfg.args,
                                    env=cfg.env or None)
        read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return SDKSession(session, stack)
