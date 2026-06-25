#!/usr/bin/env bash
#
# install.sh — set up the `mule` ed2k/Kad downloader on macOS from scratch.
#
# Installs Colima + Docker (via Homebrew), runs the MLDonkey engine in a
# container, bootstraps the Kad network + ed2k servers, and puts `mule` on
# your PATH. Safe to re-run (idempotent).
#
#   ./install.sh
#
set -euo pipefail

CONTAINER="mule-mldonkey"
IMAGE="carlonluca/mldonkey"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${MULE_DATA:-$REPO_DIR/data}"
BIN_DIR="${MULE_BIN:-/usr/local/bin}"

say()  { printf "\033[1;36m==>\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!  \033[0m %s\n" "$*"; }
die()  { printf "\033[1;31mx  \033[0m %s\n" "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || die "This installer targets macOS."

# --- 1. Homebrew -----------------------------------------------------------
command -v brew >/dev/null 2>&1 || die \
  "Homebrew is required. Install it from https://brew.sh and re-run."

# --- 2. Colima + Docker CLI ------------------------------------------------
for pkg in colima docker; do
  if brew list "$pkg" >/dev/null 2>&1; then
    say "$pkg already installed"
  else
    say "Installing $pkg ..."
    brew install "$pkg"
  fi
done

# Heal a stale Docker Desktop credential helper, if present (it breaks pulls).
CFG="$HOME/.docker/config.json"
if [ -f "$CFG" ] && grep -q '"credsStore"' "$CFG" 2>/dev/null \
   && ! command -v docker-credential-desktop >/dev/null 2>&1; then
  say "Removing stale docker credsStore"
  python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
cfg = json.load(open(p))
cfg.pop("credsStore", None); cfg.pop("credHelpers", None)
json.dump(cfg, open(p, "w"), indent=2)
PY
fi

# --- 3. Colima VM ----------------------------------------------------------
if colima status >/dev/null 2>&1; then
  say "Colima already running"
else
  say "Starting Colima (lightweight Linux VM) ..."
  colima start --cpu 2 --memory 2 --disk 20
fi

# --- 4. MLDonkey container -------------------------------------------------
mkdir -p "$DATA_DIR"
if docker inspect "$CONTAINER" >/dev/null 2>&1; then
  say "Container exists — (re)starting"
  docker start "$CONTAINER" >/dev/null
else
  say "Pulling image and creating container ..."
  docker pull "$IMAGE"
  docker run -d --name "$CONTAINER" --restart unless-stopped \
    -p 127.0.0.1:4000:4000 \
    -p 127.0.0.1:4080:4080 \
    -p 19040:19040 -p 19044:19044/udp \
    -v "$DATA_DIR":/var/lib/mldonkey \
    "$IMAGE" >/dev/null
fi

# --- 5. Install the CLI on PATH -------------------------------------------
chmod +x "$REPO_DIR/mule"
if [ -w "$BIN_DIR" ]; then
  ln -sf "$REPO_DIR/mule" "$BIN_DIR/mule"
  say "Linked mule -> $BIN_DIR/mule"
else
  say "Linking mule into $BIN_DIR (needs sudo)"
  sudo ln -sf "$REPO_DIR/mule" "$BIN_DIR/mule"
fi
MULE="$REPO_DIR/mule"

# --- 6. Wait for the console ----------------------------------------------
say "Waiting for the MLDonkey console ..."
for i in $(seq 1 30); do
  if "$MULE" console version >/dev/null 2>&1; then break; fi
  sleep 1
  [ "$i" = 30 ] && die "Console did not come up on 127.0.0.1:4000"
done

# --- 7. Bootstrap the networks --------------------------------------------
say "Enabling Kademlia + bootstrapping Kad nodes ..."
"$MULE" console "set enable_kademlia true" >/dev/null
"$MULE" console "urladd kad http://upd.emule-security.org/nodes.dat" >/dev/null
"$MULE" console "force_web_infos kad" >/dev/null
"$MULE" console "kad_web" >/dev/null

say "Adding ed2k servers from servers.txt ..."
if [ -f "$REPO_DIR/servers.txt" ]; then
  while read -r ip port _; do
    [ -z "${ip:-}" ] && continue
    case "$ip" in \#*) continue ;; esac
    "$MULE" console "n $ip $port" >/dev/null
  done < "$REPO_DIR/servers.txt"
fi
"$MULE" console "c" >/dev/null
"$MULE" console "save" >/dev/null

cat <<EOF

$(say "Done.")
  Engine:    container '$CONTAINER' (auto-restarts)
  Downloads: $DATA_DIR/incoming/files/
  CLI:       mule   (also: $REPO_DIR/mule)

Try it (Kad needs ~30-60s to warm up the first time):
  mule net
  mule search "big buck bunny"
  mule download <id>
  mule downloads

After a Mac reboot, bring the engine back up with:
  colima start && docker start $CONTAINER
EOF
