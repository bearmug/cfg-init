#!/bin/bash
set -euo pipefail

# Opt-in Bonsai 2 example profile. The generic gate installer has no model
# dependency; this script is the tested public example for OMP routing.
# Override the model/fallback identifiers only with values you control.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_MODEL="${CFG_INIT_BONSAI_MODEL:-bonsai2/qwen3.8-27b-bonsai2:medium}"
LOCAL_PROVIDER="${CFG_INIT_BONSAI_PROVIDER:-bonsai2/qwen3.8-27b-bonsai2}"
FALLBACK_MODEL="${CFG_INIT_OMP_FALLBACK:-opencode-go/gpt-5.6-luna:low}"

command -v omp >/dev/null || { echo "omp is required for the Bonsai routing example" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required for the Bonsai routing example" >&2; exit 1; }
"$ROOT_DIR/cfg-tools-model-gate.sh"

merge_record() {
	local key="$1" additions="$2" current merged
	current="$(omp config get --json "$key" 2>/dev/null || true)"
	merged="$(CURRENT="$current" ADDITIONS="$additions" python3 - <<'PY'
import json
import os
try:
    payload = json.loads(os.environ.get("CURRENT", "{}"))
except json.JSONDecodeError:
    payload = {}
if isinstance(payload, dict) and "value" in payload:
    current = payload["value"]
else:
    current = payload
if not isinstance(current, dict):
    current = {}
additions = json.loads(os.environ["ADDITIONS"])
current.update(additions)
print(json.dumps(current, separators=(",", ":")))
PY
)"
	omp config set "$key" "$merged"
}

ADDITIONS="$(LOCAL_MODEL="$LOCAL_MODEL" FALLBACK_MODEL="$FALLBACK_MODEL" python3 - <<'PY'
import json
import os
local = os.environ["LOCAL_MODEL"]
fallback = os.environ["FALLBACK_MODEL"]
print(json.dumps({
    "smol": local,
    "task": local,
    "review": local,
    "tiny": fallback,
}, separators=(",", ":")))
PY
)"
merge_record modelRoles "$ADDITIONS"

ADDITIONS="$(LOCAL_MODEL="$LOCAL_MODEL" python3 - <<'PY'
import json
import os
local = os.environ["LOCAL_MODEL"]
print(json.dumps({
    "scout": local,
    "task": local,
    "sonic": local,
    "reviewer": local,
}, separators=(",", ":")))
PY
)"
merge_record task.agentModelOverrides "$ADDITIONS"

ADDITIONS="$(LOCAL_PROVIDER="$LOCAL_PROVIDER" FALLBACK_MODEL="$FALLBACK_MODEL" python3 - <<'PY'
import json
import os
provider = os.environ["LOCAL_PROVIDER"]
fallback = os.environ["FALLBACK_MODEL"]
print(json.dumps({
    "smol": [fallback],
    "task": [fallback],
    "review": [fallback],
    "tiny": [fallback],
    provider: [fallback],
}, separators=(",", ":")))
PY
)"
merge_record retry.fallbackChains "$ADDITIONS"

echo "Bonsai 2 example routing configured; existing unrelated OMP records were preserved."
