#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec ./.venv/bin/python ./app/backend/prepdocs.py './data/*' --verbose "$@"
