# mule MCP server

Exposes the `mule` ed2k/Kad CLI as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so MCP-capable AIs (Claude Desktop, Codex CLI, Cursor, …) can search and
download with typed tools instead of shelling out.

**Prerequisite:** `mule-cli` must already be installed on the machine
(`./install.sh` at the repo root) — this connector just talks to it.

Zero dependencies: `server.py` is plain Python 3 (stdlib only) speaking MCP over
stdio. Get the absolute path to it with, from the repo root:

```bash
echo "$(pwd)/mcp/server.py"
```

Use that path in the configs below.

## Tools

`mule_ensure_engine`, `mule_net`, `mule_search`, `mule_download`,
`mule_downloads`, `mule_cancel`, `mule_commit`, `mule_download_path`.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mule": {
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/mule-cli/mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. Or, for one-click install, build a bundle (see below).

## Codex CLI

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.mule]
command = "python3"
args = ["/ABSOLUTE/PATH/TO/mule-cli/mcp/server.py"]
```

## Claude Code

Claude Code users should prefer the bundled **skill** (`skills/mule/SKILL.md`,
installed automatically). If you'd rather use the MCP server here too:

```bash
claude mcp add mule -- python3 /ABSOLUTE/PATH/TO/mule-cli/mcp/server.py
```

## Any other MCP client

Launch `python3 /ABSOLUTE/PATH/TO/mule-cli/mcp/server.py` as a stdio MCP server.

## One-click bundle (.mcpb) for Claude Desktop

`manifest.json` is ready. Build a `.mcpb` with the official packer:

```bash
cd mcp
npx @anthropic-ai/mcpb pack
```

This produces a `.mcpb` you can open with Claude Desktop to install in one click.
(The machine still needs `mule-cli` installed — the bundle is just the connector.)

## Quick smoke test

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 | python3 mcp/server.py
```
