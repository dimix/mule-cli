# mule — search & download from eMule (ed2k / Kad) via CLI

A tiny CLI that drives a headless **MLDonkey** engine (in Docker) to search and
download files from the **ed2k** and **Kad** networks — with no GUI Mac app.
Every data command supports `--json`, so it's usable both by hand and by an agent.

## Install (macOS)

You only need [Homebrew](https://brew.sh). Then:

```bash
git clone https://github.com/dimix/mule-cli.git
cd mule-cli
./install.sh
```

`install.sh` does everything: installs Colima + Docker, starts the MLDonkey engine
in a container, bootstraps Kad and the ed2k servers, and puts `mule` on your PATH.
It's idempotent (safe to re-run). Afterwards, from any directory:

```bash
mule search "big buck bunny"
mule download <id>
```

## Architecture

```
  mule  (Python, host)  ──telnet 127.0.0.1:4000──▶  MLDonkey (Docker container)
                                                        │ ed2k + Kad (serverless)
   completed downloads  ◀── ./data/incoming/files/ ◀────┘
```

- The networking (ed2k/Kad protocol, hashing, queues, sources) is done by MLDonkey.
- The CLI sends commands to MLDonkey's console and cleans up / parses the output.
- Container: `mule-mldonkey` (image `carlonluca/mldonkey`, native arm64).
- Container runtime: **Colima** (a lightweight Linux VM, installed via Homebrew).

## Where files land

| | path on the Mac |
|---|---|
| Completed | `./data/incoming/files/` |
| Partial   | `./data/temp/` |
| MLDonkey config | `./data/*.ini` |

(`./data` is mounted as `/var/lib/mldonkey` inside the container.)

## Everyday use

```bash
mule net                       # network status (is Kad connected?)
mule search interstellar       # search (waits ~35s for Kad results)
mule search "big buck bunny" --limit 15
mule results                   # re-show the last search
mule download 12               # download result #12 (multiple ids allowed)
mule downloads                 # progress of active downloads
mule pause 1 / resume 1        # pause / resume
mule cancel 1                  # cancel (handles the confirmation itself)
mule commit                    # move completed files into incoming/
```

Every data command accepts `--json`:
```bash
mule search debian --json
mule downloads --json
```

Escape hatch for raw MLDonkey console commands (debug / advanced):
```bash
mule console "vma"             # list all servers
mule console "kad_stats"
```

## Daemon management

```bash
mule daemon status             # is it up?
mule daemon start|stop|restart
mule daemon logs
```

## After a Mac reboot

Colima does not start on its own (unless you run `brew services start colima`):

```bash
colima start                   # restart the Linux VM
docker start mule-mldonkey     # the container has restart=unless-stopped
mule net                       # check that Kad reconnects
```

## Re-bootstrapping the networks (if searches stop returning results)

ed2k/Kad need to be "hooked" to some peers. The setup already does this, but if
Kad ever stops connecting:

```bash
mule console "kad_web"                                   # default Kad nodes
mule console "urladd kad http://upd.emule-security.org/nodes.dat"
mule console "force_web_infos kad"
mule console "save"
```

For **ed2k servers**, the automatic lists (server.met) are mostly dead, so it's
better to add live servers by hand with `n <ip> <port>`. The ones in `servers.txt`
were alive 2026-06 (the first one carries ~23M files):

```bash
mule console "n 45.82.80.155 5687"      # eMule Security  (most loaded)
mule console "n 176.123.5.89 4725"      # eMule Sunrise
mule console "n 91.208.162.87 4232"     # Sharing-Devils
mule console "c"                         # connect
mule console "save"
```

Note: the ipfilter (`guarding.p2p`) may flag some servers as "IP blocked".

## Notes

- The ed2k/Kad network indexes **mostly media files**: queries like "ubuntu" often
  return 0 results. Results are **not filtered**.
- The classic ed2k servers are mostly dead; real downloads go through **Kad**.
- Behind NAT without port-forwarding you get a "LowID": it works, but is slower.
  For a "HighID", forward the container's TCP/UDP ports (19040/19044) on your router.
- Only download content you have the right to download.

## AI integrations

`mule` is built to be driven by AI agents — every data command speaks `--json`.

- **Claude Code** — ships a skill at `skills/mule/SKILL.md`, auto-installed to
  `~/.claude/skills/mule/` by `install.sh`. Just ask Claude to *"search / download X
  from eMule"* and it handles engine start → search → download → reporting.
- **Claude Desktop / Codex CLI / Cursor / any MCP client** — a zero-dependency MCP
  server lives in `mcp/server.py`, exposing the same operations as typed tools.
  See [`mcp/README.md`](mcp/README.md) for per-client config and a `.mcpb` one-click
  bundle for Claude Desktop.
- **Any shell-based agent** — see [`AGENTS.md`](AGENTS.md) for the plain-CLI playbook.

## Installed stack

- `brew install colima docker`
- image `carlonluca/mldonkey` (ports: 4000 console, 4080 web, 19040/19044 p2p)
- the CLI is just `mule` (Python 3, no external dependencies)

## Disclaimer / lawful use

`mule-cli` is a **client** for the ed2k/Kad P2P networks — like aMule, eMule, or
any BitTorrent client. It hosts and distributes nothing: it only talks to an
existing public network.

Responsibility for **what** is searched and downloaded lies entirely with the
person using the tool. Use it only for files you have the right to download (free
software, public-domain works, your own content, or anything licensed to allow it),
and in compliance with the copyright laws of your country. The software is provided
"as is", without warranty (see `LICENSE`).
