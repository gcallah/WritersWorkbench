#!/bin/bash
# tests.sh: run all the tests (lint included) against a fresh test database.
#
# usage: bin/tests.sh [-c core_dir]
#   -c   test against the backendcore in a local BackEndCore checkout
#        (e.g. ~/Business/BackEndCore) instead of the installed one
#
# Uses the project's venv (.venv in a Superset workspace, otherwise
# WritersWorkbench-venv) if there is one. Only the test database
# (database/test_sql.db) is removed first; the dev database is kept.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

core=""
while getopts "c:" opt; do
    case $opt in
        c) core=$(cd "$OPTARG" && pwd) ;;
        *) sed -n '2,10p' "$0"; exit 2 ;;
    esac
done

for venv in .venv WritersWorkbench-venv; do
    if [ -f "$venv/bin/activate" ]; then
        . "$venv/bin/activate"
        break
    fi
done

export PYTHONPATH="${core:+$core:}$PWD"
echo "backendcore: $(python3 -c 'import backendcore, os
print(os.path.dirname(backendcore.__file__))')"
rm -f database/test_sql.db
make all_tests
