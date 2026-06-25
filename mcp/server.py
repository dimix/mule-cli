#!/usr/bin/env python3
"""
mule MCP server — exposes the `mule` ed2k/Kad CLI as Model Context Protocol tools.

Zero dependencies: implements the MCP stdio transport (newline-delimited
JSON-RPC 2.0) by hand, and shells out to the `mule` CLI (which must be on PATH).

Works with any MCP client: Claude Desktop, Codex CLI, Cursor, etc.
Configure the client to launch:  python3 /path/to/mcp/server.py
"""

import json
import subprocess
import sys

SERVER_NAME = "mule-cli"
SERVER_VERSION = "1.1.0"
DEFAULT_PROTOCOL = "2025-06-18"
CONTAINER = "mule-mldonkey"

# --------------------------------------------------------------------------
# Helpers to drive the CLI
# --------------------------------------------------------------------------
def run(args, timeout=120):
    """Run a command, return (ok, text)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out.strip()
    except subprocess.TimeoutExpired:
        return False, f"timeout running: {' '.join(args)}"
    except FileNotFoundError:
        return False, "the `mule` CLI was not found on PATH (is mule-cli installed?)"


def ensure_engine():
    script = (
        "colima status >/dev/null 2>&1 || colima start; "
        f"docker start {CONTAINER} >/dev/null 2>&1; "
        "for i in $(seq 1 30); do mule console version >/dev/null 2>&1 && break; sleep 1; done; "
        "mule daemon status"
    )
    ok, out = run(["bash", "-lc", script], timeout=180)
    return ok, out or "engine ensured"


def download_path():
    ok, src = run(["docker", "inspect", CONTAINER,
                   "--format", "{{range .Mounts}}{{.Source}}{{end}}"])
    if ok and src:
        return src + "/incoming/files/"
    return "(could not resolve — is the container present?)"


# --------------------------------------------------------------------------
# Tool definitions + dispatch
# --------------------------------------------------------------------------
TOOLS = [
    {
        "name": "mule_ensure_engine",
        "description": "Start the MLDonkey engine (Colima VM + Docker container) if "
                       "it isn't running, and wait until the console responds. Call "
                       "this first if searches or status calls fail.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mule_net",
        "description": "Report network status: whether Kad (serverless) is connected "
                       "and how many ed2k servers are connected. Returns JSON.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mule_search",
        "description": "Search the ed2k/Kad networks. Returns JSON results sorted by "
                       "source count (descending). The `id` of a result is used to "
                       "download it, and is only valid until the next search. The "
                       "network indexes mostly media; generic queries can return 0.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "search keywords"},
                "wait": {"type": "integer", "default": 35,
                         "description": "seconds to wait for results (Kad is slow)"},
                "limit": {"type": "integer", "default": 25,
                          "description": "max results to return (0 = all)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "mule_download",
        "description": "Start downloading one or more result ids from the most recent "
                       "search. Returns JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "integer"},
                        "description": "result ids from the last search"},
            },
            "required": ["ids"],
        },
    },
    {
        "name": "mule_downloads",
        "description": "List active downloads with state and percent complete. JSON.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mule_cancel",
        "description": "Cancel one or more downloads by id (handles confirmation).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["ids"],
        },
    },
    {
        "name": "mule_commit",
        "description": "Move completed downloads into the incoming/ folder.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mule_download_path",
        "description": "Return the host filesystem path where completed files land.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def call_tool(name, args):
    args = args or {}
    if name == "mule_ensure_engine":
        return ensure_engine()[1]
    if name == "mule_net":
        return run(["mule", "net", "--json"])[1]
    if name == "mule_search":
        q = str(args.get("query", "")).strip()
        if not q:
            return "error: 'query' is required"
        wait = str(int(args.get("wait", 35)))
        limit = str(int(args.get("limit", 25)))
        return run(["mule", "search", q, "--wait", wait,
                    "--limit", limit, "--json"], timeout=int(wait) + 60)[1]
    if name == "mule_download":
        ids = [str(int(i)) for i in args.get("ids", [])]
        if not ids:
            return "error: 'ids' is required"
        return run(["mule", "download", *ids, "--json"])[1]
    if name == "mule_downloads":
        return run(["mule", "downloads", "--json"])[1]
    if name == "mule_cancel":
        ids = [str(int(i)) for i in args.get("ids", [])]
        if not ids:
            return "error: 'ids' is required"
        return run(["mule", "cancel", *ids])[1]
    if name == "mule_commit":
        return run(["mule", "commit"])[1]
    if name == "mule_download_path":
        return download_path()
    return f"error: unknown tool '{name}'"


# --------------------------------------------------------------------------
# JSON-RPC / MCP stdio loop
# --------------------------------------------------------------------------
def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(req):
    method = req.get("method")
    rid = req.get("id")

    if method == "initialize":
        proto = (req.get("params") or {}).get("protocolVersion", DEFAULT_PROTOCOL)
        return {
            "jsonrpc": "2.0", "id": rid,
            "result": {
                "protocolVersion": proto,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params") or {}
        try:
            text = call_tool(params.get("name"), params.get("arguments"))
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": text or "(no output)"}]}}
        except Exception as e:  # noqa: BLE001 — surface any failure to the client
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text", "text": f"error: {e}"}],
                               "isError": True}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}

    # Notifications (no id) get no response.
    if rid is None:
        return None
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
