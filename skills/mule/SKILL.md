---
name: mule
description: Search for and download files from the eMule ed2k/Kad peer-to-peer networks using the `mule` CLI installed on this machine. Use whenever the user wants to find or download a file (ebook, video, music, software, document) from eMule / ed2k / Kad / MLDonkey, or mentions mule / mule-cli. Covers starting the engine, searching, downloading, tracking progress, and reporting where the file lands.
---

# mule — eMule (ed2k / Kad) search & download

`mule` is a CLI already installed on this machine (on `PATH`). It drives a headless
MLDonkey engine running in a Docker container (`mule-mldonkey`) under Colima.
**Every data command supports `--json`** — always pass `--json` and parse that,
never scrape the human table.

Repo / source: https://github.com/dimix/mule-cli

## Workflow

### 1. Make sure the engine is up (do this first, every session)

```bash
mule daemon status
```

If it does **not** print `Up …`, bring the stack up (Colima doesn't auto-start
after a reboot):

```bash
colima status >/dev/null 2>&1 || colima start
docker start mule-mldonkey >/dev/null 2>&1
for i in $(seq 1 30); do mule console version >/dev/null 2>&1 && break; sleep 1; done
```

Then confirm the networks are connected:

```bash
mule net --json     # -> {"kad_connected": true, "servers": "...Connected to N..."}
```

Kad needs ~30–60s to warm up the first time after a (re)start. If `kad_connected`
is false, wait ~30s and re-check before searching.

### 2. Search

```bash
mule search "the query" --json
```

Returns:
```json
{"query":"...","count":42,"total":42,
 "results":[{"id":12,"name":"...","size":"848K","size_bytes":868352,
             "sources":3,"ed2k":"<MD4 HEX>"}, ...]}
```

- Results are **already sorted by `sources` (descending)**. More sources = faster,
  more reliable download. Prefer high-source results.
- `id` is what you pass to `download` — but it is **only valid for the most recent
  search**. To reuse ids without re-searching: `mule results --json`.
- The network indexes **mostly media** (video/audio/ebooks). Generic queries like
  "ubuntu" or "debian" often return 0 — that's normal, not a failure.
- Default wait is 35s. For sparse queries you can extend: `--wait 45`.

Present the best few results to the user (name, size, sources) and **confirm which
one to download** before downloading — downloads cost bandwidth/time and the network
is unfiltered. Don't auto-pick unless the user already named a specific file.

### 3. Download

```bash
mule download <id>          # one or more ids: mule download 12 5
```

Then poll progress:
```bash
mule downloads --json
# -> {"count":1,"rate":"10.1 KB/s",
#     "downloads":[{"id":2,"state":"downloading","name":"...","percent":"63.7%","size":"848K"}]}
```

When the file disappears from `downloads` (or reaches ~100%), finalize it:
```bash
mule commit
```

Small files (ebooks ~1 MB) finish in seconds; large videos with few sources can be
very slow — set expectations with the user.

### 4. Tell the user where the file is

Completed files land in the container's mounted volume, on the host at
`<data-dir>/incoming/files/`. Resolve the real host path with:

```bash
docker inspect mule-mldonkey --format '{{range .Mounts}}{{.Source}}{{end}}'
```
→ append `/incoming/files/`. Optionally verify integrity (e.g. `file <path>`).

## Other commands

```bash
mule pause <id> / resume <id>     # pause / resume a download
mule cancel <id>                  # cancel (handles its own confirmation)
mule console "<raw cmd>"          # raw MLDonkey console (e.g. "vma", "kad_stats")
mule daemon start|stop|restart|logs
```

## If searches stop returning anything

Usually the ed2k servers dropped or Kad lost peers. Re-bootstrap:
```bash
mule console "kad_web"
mule console "n 45.82.80.155 5687"   # eMule Security (large, reliable)
mule console "c"
mule console "save"
```
The repo's `servers.txt` holds more known-good servers.

## Guardrails

- Only help download content the user has the right to download (free software,
  public-domain works, their own files, openly-licensed media). It's a P2P client;
  responsibility for the content is the user's.
- Results are unfiltered — surface names plainly but don't editorialize.
