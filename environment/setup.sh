#!/bin/sh
# Create the environment of the analytic tier in <env-dir>/analytic (default: next to the package).
# Usage: QUTEST_SRC=<QUTest 0.1.0 source tree> sh environment/setup.sh [<env-dir>]
set -eu
here=$(cd "$(dirname "$0")" && pwd)
env=${1:-$here/../../qsurvdiag-env}
commit=c56e5a83f3b600a893e0d897ed86c705d25eb104
: "${QUTEST_SRC:?set QUTEST_SRC to a QUTest 0.1.0 source tree}"
[ -d "$QUTEST_SRC" ] || { echo "QUTEST_SRC is not a directory: $QUTEST_SRC" >&2; exit 1; }
if [ -e "$QUTEST_SRC/.git" ] && [ "$(git -C "$QUTEST_SRC" rev-parse HEAD)" != "$commit" ]; then
    echo "QUTEST_SRC is not at commit $commit, which the study used" >&2
    exit 1
fi
command -v python3.12 >/dev/null || { echo "python3.12 not found" >&2; exit 1; }
python3.12 -m venv "$env/analytic"
"$env/analytic/bin/pip" install -r "$here/requirements-analytic.txt"
"$env/analytic/bin/pip" install "$QUTEST_SRC"
