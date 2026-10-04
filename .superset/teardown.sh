#!/bin/bash
# Superset workspace teardown: stop the dev server, release the port.
set -uo pipefail
. "$SUPERSET_ROOT_PATH/.superset/lib.sh"

if [ -s "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null && echo "Stopped dev server"
    rm -f "$PID_FILE"
fi
# The flask debug reloader forks a child that may outlive its parent.
if [ -s "$PORT_FILE" ]; then
    pids=$(lsof -tiTCP:"$(cat "$PORT_FILE")" -sTCP:LISTEN 2>/dev/null)
    [ -n "$pids" ] && kill $pids 2>/dev/null
fi
release_port
exit 0
