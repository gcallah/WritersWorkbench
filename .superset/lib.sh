# Shared helpers for the Superset lifecycle scripts; sourced, not run.

ROOT="${SUPERSET_ROOT_PATH:?SUPERSET_ROOT_PATH not set}"
WS="${SUPERSET_WORKSPACE_PATH:-$PWD}"
mkdir -p "$WS/.superset"

# One directory per claimed port; mkdir is atomic, so it doubles as a lock.
PORT_DIR="$HOME/.superset/port-allocations/$(basename "$ROOT")"
PORT_FILE="$WS/.superset/port"
PID_FILE="$WS/.superset/server.pid"
BASE_PORT=8001
MAX_PORT=8099

port_in_use() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# Claim a free port for this workspace (reusing an earlier claim).
claim_port() {
    if [ -s "$PORT_FILE" ]; then
        cat "$PORT_FILE"
        return
    fi
    mkdir -p "$PORT_DIR"
    local port
    for port in $(seq "$BASE_PORT" "$MAX_PORT"); do
        port_in_use "$port" && continue
        if mkdir "$PORT_DIR/$port" 2>/dev/null; then
            echo "$WS" > "$PORT_DIR/$port/owner"
            echo "$port" > "$PORT_FILE"
            echo "$port"
            return
        fi
    done
    echo "No free port in $BASE_PORT-$MAX_PORT" >&2
    return 1
}

release_port() {
    [ -s "$PORT_FILE" ] || return 0
    rm -rf "$PORT_DIR/$(cat "$PORT_FILE")"
    rm -f "$PORT_FILE"
}
