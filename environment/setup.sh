#!/bin/sh
# Create the analytic-tier environment outside the package directory.
# Usage: QUTEST_SRC=<QUTest 0.1.0 source tree> sh environment/setup.sh <env-dir>
set -e
ENV="${1:-../qsurvdiag-env}"
: "${QUTEST_SRC:?set QUTEST_SRC to a QUTest 0.1.0 source tree}"
python3.12 -m venv "$ENV/analytic"
"$ENV/analytic/bin/pip" install -r environment/requirements-analytic.txt
"$ENV/analytic/bin/pip" install "$QUTEST_SRC"
