#!/bin/bash
# push.sh: rebase the current branch onto origin, then push it.
#
# usage: bin/push.sh
#
# Commit first: this refuses to run with uncommitted changes. If someone
# else has pushed in the meantime, their commits come first and yours are
# replayed on top of them.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

branch=$(git branch --show-current)
[ -n "$branch" ] || { echo "push.sh: not on a branch" >&2; exit 1; }
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "push.sh: commit your changes first" >&2
    exit 1
fi
git pull --rebase origin "$branch"
git push origin "$branch"
