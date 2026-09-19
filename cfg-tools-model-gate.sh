#!/bin/bash
set -euo pipefail

# Optional local-model routing for Oh My Pi.
# The gate is model-agnostic; Bonsai 2 is the tested default example.
# Override MODEL_GATE_UPSTREAM, MODEL_GATE_PORT, and MODEL_GATE_LIMIT before
# starting the gate when using another OpenAI-compatible local server.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE_SRC="$ROOT_DIR/home/.local/share/model-gate/model-gate-proxy.mjs"
GATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/model-gate"
GATE_DST="$GATE_DIR/model-gate-proxy.mjs"

command -v bun >/dev/null || { echo "bun is required to run the model gate" >&2; exit 1; }
command -v omp >/dev/null || { echo "omp is required to configure subagent routing" >&2; exit 1; }

mkdir -p "$GATE_DIR"
cp -f "$GATE_SRC" "$GATE_DST"

merge_record() {
	local key="$1" additions="$2" current merged
	current="$(omp config get "$key" 2>/dev/null || printf '{}')"
	merged="$(CURRENT="$current" ADDITIONS="$additions" python3 - <<'PY'
import json, os
current = json.loads(os.environ["CURRENT"] or "{}")
additions = json.loads(os.environ["ADDITIONS"])
if not isinstance(current, dict):
    raise SystemExit("expected a record for " + os.environ.get("KEY", "setting"))
current.update(additions)
print(json.dumps(current, separators=(",", ":")))
PY
)"
	omp config set "$key" "$merged"
}

# Merge only the keys owned by this optional layer; unrelated user settings stay intact.
merge_record modelRoles '{"smol":"bonsai2/qwen3.8-27b-bonsai2:medium","task":"bonsai2/qwen3.8-27b-bonsai2:medium","review":"bonsai2/qwen3.8-27b-bonsai2:medium","tiny":"opencode-go/gpt-5.6-luna:low"}'
merge_record task.agentModelOverrides '{"scout":"bonsai2/qwen3.8-27b-bonsai2:medium","task":"bonsai2/qwen3.8-27b-bonsai2:medium","sonic":"bonsai2/qwen3.8-27b-bonsai2:medium","reviewer":"bonsai2/qwen3.8-27b-bonsai2:medium"}'
merge_record retry.fallbackChains '{"smol":["opencode-go/gpt-5.6-luna:low"],"task":["opencode-go/gpt-5.6-luna:low"],"review":["opencode-go/gpt-5.6-luna:low"],"tiny":["opencode-go/gpt-5.6-luna:low"],"bonsai2/qwen3.8-27b-bonsai2":["opencode-go/gpt-5.6-luna:low"]}'

echo "Model gate installed at $GATE_DST"
echo "Start under your process supervisor, for example:"
echo "  bun $GATE_DST"
echo "Default upstream: http://127.0.0.1:8080; gate: http://127.0.0.1:8090"
