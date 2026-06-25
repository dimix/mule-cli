# AGENTS.md — driving `mule` from an AI agent

This file tells any AI coding agent (Codex CLI, Cursor, Claude, etc.) how to use the
`mule` CLI to search and download from the eMule **ed2k / Kad** networks.

`mule` is on `PATH`. **Every data command supports `--json`** — always use `--json`
and parse that; never scrape the human-readable table.

## 1. Ensure the engine is running (first, every session)

The MLDonkey engine runs in Docker under Colima, which does not auto-start after a
reboot. Before searching:

```bash
mule daemon status                      # expect "Up ..."
# if not up:
colima status >/dev/null 2>&1 || colima start
docker start mule-mldonkey >/dev/null 2>&1
for i in $(seq 1 30); do mule console version >/dev/null 2>&1 && break; sleep 1; done
mule net --json                         # -> {"kad_connected": true, ...}
```

Kad needs ~30–60s to warm up after a (re)start.

## 2. Search → download → finalize

```bash
mule search "the query" --json          # results sorted by `sources` (desc)
mule download <id>                      # id from the LAST search only
mule downloads --json                   # poll progress
mule commit                             # move completed into incoming/
```

Result objects: `{"id","name","size","size_bytes","sources","ed2k"}`. Prefer high
`sources`. Re-fetch last results without re-searching: `mule results --json`.

Find where completed files land:
```bash
docker inspect mule-mldonkey --format '{{range .Mounts}}{{.Source}}{{end}}'
# append /incoming/files/
```

## 3. Etiquette

- Present the best results and **confirm the choice with the user** before
  downloading (bandwidth/time; the network is unfiltered).
- The network is mostly media — generic queries (e.g. "ubuntu") often return 0.
- Only help download content the user has the right to download. The user owns
  responsibility for the content; `mule` is just a P2P client.

## Prefer typed tools? Use the MCP server

If your runtime speaks MCP, use `mcp/server.py` instead of shelling out — it exposes
the same operations as typed tools. See `mcp/README.md` for client configuration
(Claude Desktop, Codex CLI, and generic MCP).
