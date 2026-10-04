#!/bin/bash
# Superset run command: start the Flask dev server on this workspace's port.
# Mirrors local.sh, which hard-codes port 8000.
set -euo pipefail
. "$SUPERSET_ROOT_PATH/.superset/lib.sh"
cd "$WS"

PORT=$(claim_port)
export PYTHONPATH="${PYTHONPATH:-}:$WS"
export FLASK_ENV=development
export PROJ_DIR="$WS"
export DEBUG=1
export DATABASE=sqlite
export SQLITE_LOC="$WS/database"
. .venv/bin/activate

echo "Starting API server on http://127.0.0.1:$PORT"
echo $$ > "$PID_FILE"
FLASK_APP=server.endpoints exec flask run --debug --host=127.0.0.1 --port="$PORT"
