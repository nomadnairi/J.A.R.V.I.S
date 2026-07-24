"""MCP (Model Context Protocol) client — mount external agent tools as skills."""

from jarvis.mcp.base import MCPServerConfig, MCPSession, MCPTool
from jarvis.mcp.config import load_servers, parse_servers
from jarvis.mcp.manager import MCPManager, ServerStatus
from jarvis.mcp.skill import MCPToolSkill, namespaced_name

__all__ = [
    "MCPServerConfig",
    "MCPSession",
    "MCPTool",
    "MCPManager",
    "ServerStatus",
    "MCPToolSkill",
    "namespaced_name",
    "load_servers",
    "parse_servers",
]
