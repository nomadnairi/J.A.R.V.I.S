"""Load MCP server definitions from settings (a JSON file or inline JSON)."""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.mcp.base import MCPServerConfig
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


def parse_servers(data: dict) -> list[MCPServerConfig]:
    """Parse a ``{"mcpServers": {name: spec}}`` (or bare ``{name: spec}``) dict."""
    servers = data.get("mcpServers", data) if isinstance(data, dict) else {}
    out: list[MCPServerConfig] = []
    for name, spec in (servers or {}).items():
        if not isinstance(spec, dict):
            continue
        cfg = MCPServerConfig.from_spec(name, spec)
        if cfg.is_valid():
            out.append(cfg)
        else:
            logger.warning("MCP server %r skipped: invalid config.", name)
    return out


def load_servers(settings) -> list[MCPServerConfig]:
    """Read MCP servers from ``mcp_config_path`` (file) or ``mcp_servers`` (inline)."""
    # A file path takes precedence; inline JSON is the fallback.
    raw = ""
    path = getattr(settings, "mcp_config_path", "")
    if path:
        p = Path(path)
        if p.is_file():
            raw = p.read_text(encoding="utf-8")
        else:
            logger.warning("MCP_CONFIG_PATH %s not found.", path)
    if not raw:
        raw = getattr(settings, "mcp_servers", "") or ""
    raw = raw.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse MCP config JSON: %s", exc)
        return []
    return parse_servers(data)
