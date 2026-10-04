#!/bin/bash
# Superset workspace setup: venv + deps, untracked files, a private port.
set -euo pipefail
. "$SUPERSET_ROOT_PATH/.superset/lib.sh"
cd "$WS"

# Copy untracked config the main checkout has but git doesn't.
for f in .env .env.local .envrc; do
    if [ -f "$ROOT/$f" ] && [ ! -e "$WS/$f" ]; then
        cp "$ROOT/$f" "$WS/$f"
        echo "Copied $f"
    fi
done

# requirements.txt pulls BackEndCore over ssh, so an ssh key must be loaded.
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip

# Pin to the main checkout's venv when there is one: newer releases of some
# deps (e.g. cryptography) may lack wheels for this Python and fail to build.
CONSTRAINTS=()
MAIN_PIP="$ROOT/$(basename "$ROOT")-venv/bin/pip"
if [ -x "$MAIN_PIP" ]; then
    "$MAIN_PIP" freeze | grep -iv '^backendcore' > .superset/constraints.txt
    CONSTRAINTS=(-c .superset/constraints.txt)
fi
.venv/bin/pip install --quiet -r requirements-dev.txt ${CONSTRAINTS[@]+"${CONSTRAINTS[@]}"}

echo "Dev server port for this workspace: $(claim_port)"
