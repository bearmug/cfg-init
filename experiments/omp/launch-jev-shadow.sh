#!/bin/sh
set -eu
umask 077
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BASE="$HOME/.omp/agent/cache/decider-shadow"
STATS="$HOME/.omp/agent/telemetry/decider-jev"
UNTIL="$("$BASE/.venv/bin/python" -c 'import json; from pathlib import Path; print(json.loads((Path.home()/".omp/agent/telemetry/decider-jev/trial.json").read_text())["until"])')"
exec "$BASE/.venv/bin/python" "$SCRIPT_DIR/shadow-proxy.py" --remote-url https://api.typesafe.ai --stats "$STATS/requests.jsonl" --until "$UNTIL"
