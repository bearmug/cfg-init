#!/bin/bash
set -euo pipefail

# Install the model-agnostic Bun gate. This recipe only copies the proxy;
# provider/model routing belongs in an explicit optional profile such as
# cfg-tools-model-gate-bonsai.sh.
# Override MODEL_GATE_UPSTREAM, MODEL_GATE_PORT, and MODEL_GATE_LIMIT when
# starting the copied proxy for another OpenAI-compatible local server.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE_SRC="$ROOT_DIR/home/.local/share/model-gate/model-gate-proxy.mjs"
GATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/model-gate"
GATE_DST="$GATE_DIR/model-gate-proxy.mjs"

command -v bun >/dev/null || { echo "bun is required to run the model gate" >&2; exit 1; }
mkdir -p "$GATE_DIR"
cp -f "$GATE_SRC" "$GATE_DST"

echo "Model gate installed at $GATE_DST"
echo "Start under a process supervisor, for example:"
echo "  bun $GATE_DST"
echo "Default upstream: http://127.0.0.1:8080; gate: http://127.0.0.1:8090"
