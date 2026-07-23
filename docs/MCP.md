# MCP — mount external agent skills as tools

J.A.R.V.I.S. is an **MCP client**. It connects to Model Context Protocol servers —
the open standard used by the **agentskills.io** ecosystem, **Hermes Agent**,
Claude and others — discovers their tools, and mounts each one as a native skill
the assistant can call. Your product layer (bot, tiers, desktop) stays; you gain
the whole MCP tool ecosystem.

## Enable it

```bash
pip install mcp            # the optional SDK (or: pip install ".[mcp]")
```

In your `.env`:

```env
MCP_ENABLED=true
# Either point at a JSON file …
MCP_CONFIG_PATH=/opt/jarvis/mcp.json
# … or paste the JSON inline (same shape):
MCP_SERVERS={"mcpServers":{"fs":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/data"]}}}
```

The config uses the **standard `mcpServers` shape** (identical to Claude/Hermes),
so you can reuse an existing file:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
    },
    "hermes": { "url": "https://your-hermes-host/sse" }
  }
}
```

Two transports are supported: **stdio** (a local subprocess: `command` + `args`)
and **sse** (a remote endpoint: `url`).

## What happens

On startup J.A.R.V.I.S. connects each server, lists its tools and registers them
as skills named `<server>__<tool>` (e.g. `filesystem__read_file`). They appear in
the model's tool list automatically. A server that fails to connect is skipped —
it never blocks startup. Connection results show in the logs and `/doctor`.

## Notes

- Tools run in the MCP server's own process/sandbox, not J.A.R.V.I.S.'s file
  sandbox — trust the servers you add.
- No `mcp` package installed → MCP is silently disabled with a hint in the log.
