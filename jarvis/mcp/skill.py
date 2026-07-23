"""Wrap a remote MCP tool as a native J.A.R.V.I.S. skill."""

from __future__ import annotations

import re

from jarvis.mcp.base import MCPSession, MCPTool
from jarvis.skills.base import BaseSkill, SkillResult

#: Tool names exposed to the LLM must match this (OpenAI/Anthropic constraint).
_SAFE = re.compile(r"[^a-zA-Z0-9_-]")

#: A permissive default schema for tools that advertise no input schema.
_DEFAULT_SCHEMA = {"type": "object", "properties": {}}


def namespaced_name(server: str, tool: str) -> str:
    """Collision-proof, LLM-safe tool name: ``<server>__<tool>``."""
    raw = f"{server}__{tool}"
    return _SAFE.sub("_", raw)[:64]


class MCPToolSkill(BaseSkill):
    """Exposes one MCP tool to the model; execution proxies to the server."""

    priority = 15

    def __init__(self, session: MCPSession, tool: MCPTool, server: str) -> None:
        self.session = session
        self.tool = tool
        self.server = server
        self.name = namespaced_name(server, tool.name)
        base_desc = tool.description or f"{tool.name} (via {server})"
        self.description = f"[{server}] {base_desc}"[:1024]
        self.parameters = tool.input_schema or _DEFAULT_SCHEMA

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()

    async def execute(self, **kwargs: object) -> SkillResult:
        try:
            result = await self.session.call_tool(self.tool.name, dict(kwargs))
        except Exception as exc:  # noqa: BLE001 - a remote tool must not crash us
            return SkillResult(text=f"MCP tool '{self.name}' failed: {exc}")
        return SkillResult(text=str(result))
