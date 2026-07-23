"""Tests for the MCP client: config parsing, tool wrapping, manager discovery."""

from __future__ import annotations

import json

import pytest

from jarvis.mcp.base import MCPServerConfig, MCPSession, MCPTool
from jarvis.mcp.config import load_servers, parse_servers
from jarvis.mcp.manager import MCPManager
from jarvis.mcp.skill import MCPToolSkill, namespaced_name


# -- config parsing -----------------------------------------------------------


def test_parse_stdio_and_sse_servers():
    data = {"mcpServers": {
        "fs": {"command": "npx", "args": ["-y", "server-fs", "/tmp"]},
        "remote": {"url": "https://example.com/sse"},
        "bad": {"description": "no command or url"},
    }}
    servers = {s.name: s for s in parse_servers(data)}
    assert servers["fs"].transport == "stdio" and servers["fs"].command == "npx"
    assert servers["remote"].transport == "sse"
    assert "bad" not in servers               # invalid config dropped


def test_load_servers_from_inline_json(tmp_path):
    class S:
        mcp_config_path = ""
        mcp_servers = json.dumps({"mcpServers": {
            "fs": {"command": "run-fs"}}})
    servers = load_servers(S())
    assert len(servers) == 1 and servers[0].command == "run-fs"


def test_load_servers_from_file_takes_precedence(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"x": {"command": "c"}}}),
                encoding="utf-8")

    class S:
        mcp_config_path = str(cfg)
        mcp_servers = ""
    servers = load_servers(S())
    assert [s.name for s in servers] == ["x"]


def test_load_servers_bad_json_is_empty():
    class S:
        mcp_config_path = ""
        mcp_servers = "{not json"
    assert load_servers(S()) == []


# -- tool → skill wrapping ----------------------------------------------------


def test_namespaced_name_is_llm_safe():
    assert namespaced_name("my server", "read/file") == "my_server__read_file"


@pytest.mark.asyncio
async def test_mcp_tool_skill_executes_via_session():
    class FakeSession(MCPSession):
        async def list_tools(self):
            return []

        async def call_tool(self, name, arguments):
            return f"called {name} with {arguments}"

    tool = MCPTool(name="echo", description="Echo it",
                input_schema={"type": "object",
                                "properties": {"x": {"type": "string"}}})
    skill = MCPToolSkill(FakeSession(), tool, "srv")
    assert skill.name == "srv__echo"
    assert skill.parameters["properties"] == {"x": {"type": "string"}}
    spec = skill.as_tool_spec()
    assert spec is not None and spec.name == "srv__echo"
    out = await skill.execute(x="hi")
    assert "called echo" in out.text and "'x': 'hi'" in out.text


@pytest.mark.asyncio
async def test_mcp_tool_skill_survives_remote_error():
    class Boom(MCPSession):
        async def list_tools(self):
            return []

        async def call_tool(self, name, arguments):
            raise RuntimeError("server down")

    skill = MCPToolSkill(Boom(), MCPTool(name="t"), "srv")
    out = await skill.execute()
    assert "failed" in out.text.lower()


# -- manager discovery --------------------------------------------------------


class _FakeSession(MCPSession):
    def __init__(self, tools):
        self._tools = tools
        self.closed = False

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name, arguments):
        return "ok"

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_manager_discovers_and_wraps_tools():
    cfg = MCPServerConfig(name="srv", command="c")
    session = _FakeSession([MCPTool("a"), MCPTool("b")])

    async def factory(_cfg):
        return session

    mgr = MCPManager([cfg], session_factory=factory)
    skills = await mgr.start()
    assert {s.name for s in skills} == {"srv__a", "srv__b"}
    assert mgr.statuses()[0].connected and mgr.statuses()[0].tool_count == 2
    await mgr.stop()
    assert session.closed is True


@pytest.mark.asyncio
async def test_manager_skips_failed_server():
    async def factory(_cfg):
        raise RuntimeError("cannot connect")

    mgr = MCPManager([MCPServerConfig(name="down", command="c")],
                    session_factory=factory)
    skills = await mgr.start()
    assert skills == []
    assert mgr.statuses()[0].connected is False


@pytest.mark.asyncio
async def test_engine_mounts_mcp_tools_on_start():
    from jarvis.config.settings import Settings
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine
    from jarvis.llm.client import LLMClient
    from tests.conftest import FakeProvider

    settings = Settings(log_file="", memory_enabled=False,
                        integrations_enabled=False, goals_enabled=False,
                        rate_limit_enabled=False, mcp_enabled=True,
                        mcp_servers=json.dumps({"mcpServers": {
                            "srv": {"command": "c"}}}))
    container = ServiceContainer(settings, llm_client=LLMClient(FakeProvider()))
    engine = JarvisEngine(container=container)
    # Swap in a fake manager so no real subprocess is spawned.
    engine.mcp = MCPManager([MCPServerConfig(name="srv", command="c")],
                            session_factory=lambda c: _wrap(
                                _FakeSession([MCPTool("ping")])))
    await engine.start()
    assert engine.skills.get("srv__ping") is not None
    await engine.shutdown()


async def _wrap(session):
    return session


# -- bot screen ---------------------------------------------------------------


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_mcp_screen_lists_servers_and_tools():
    from jarvis.interfaces.bot_menu import screen_mcp
    from jarvis.mcp.manager import ServerStatus

    statuses = [ServerStatus("fs", True, tool_count=2),
                ServerStatus("down", False, detail="cannot connect")]
    text, rows = screen_mcp("en", statuses, ["fs__read", "fs__write"])
    assert "fs" in text and "2 🔧" in text
    assert "❌" in text and "cannot connect" in text
    assert "fs__read" in text
    assert "m:settings" in _flat(rows) and "m:close" in _flat(rows)


def test_mcp_screen_empty():
    from jarvis.interfaces.bot_menu import screen_mcp
    text, _rows = screen_mcp("en", [], [])
    assert "No MCP servers" in text


def test_settings_shows_mcp_button_when_enabled():
    from jarvis.interfaces.bot_menu import screen_settings
    _t, on = screen_settings("en", multi_model=False, mcp_on=True)
    assert "m:mcp" in _flat(on)
    _t2, off = screen_settings("en", multi_model=False, mcp_on=False)
    assert "m:mcp" not in _flat(off)
