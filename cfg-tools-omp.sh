#!/bin/bash

# ========================================================================
# OMP coding agent setup: token-spend tuning + headroom MCP compression.
# Applies per-key so existing providers/models on the machine are kept.
# ========================================================================
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Install the local context-compression tool and TypeScript LSP prerequisites.
uv tool install --python 3.13 "headroom-ai[all]"
bun install -g typescript typescript-language-server@6.0.1
LSP_BIN="$(command -v typescript-language-server)"

# ------------------------------------------------------------------------
# spend and agent tuning (config CLI updates individual leaves)
# ------------------------------------------------------------------------
omp config set compaction.thresholdTokens -- -1
omp config set compaction.thresholdPercent 80
omp config set compaction.keepRecentTokens 20000
omp config set compaction.idleEnabled true
omp config set compaction.idleThresholdTokens 200000
omp config set compaction.idleTimeoutSeconds 180
omp config set compaction.v2RetainedMessageBudget 32000
omp config set compaction.experimentalContextManagement false
omp config set display.showTokenUsage true
omp config set display.cacheMissMarker true
omp config set snapcompact.shape auto
omp config set snapcompact.systemPrompt none
omp config set snapcompact.toolResults true
omp config set task.enableLsp true
omp config set task.maxRecursionDepth 1
omp config set recap.idleSeconds 600
omp config set advisor.maxNotesPerUpdate 1
python3 - <<'EOF'
import json, subprocess
def get_record(key):
    return json.loads(subprocess.check_output(
        ["omp", "config", "get", key, "--json"], text=True
    ))["value"]
def put_record(key, value):
    subprocess.run(["omp", "config", "set", key, json.dumps(value)], check=True)
roles = get_record("modelRoles")
roles["judge"] = "typesafe/jev-latest"
put_record("modelRoles", roles)
fallbacks = get_record("retry.fallbackChains")
fallbacks["judge"] = ["opencode-zen-jev/jev-1.13"]
put_record("retry.fallbackChains", fallbacks)
EOF

# ------------------------------------------------------------------------
# delegation preprompt, headroom MCP and TypeScript LSP; preserve unrelated content
# ------------------------------------------------------------------------
mkdir -p "$HOME/.omp/agent"
python3 - "$HOME/.omp/agent/APPEND_SYSTEM.md" "$SCRIPT_DIR/home/.omp/agent/APPEND_SYSTEM.md" <<'EOF'
import re, sys
from pathlib import Path

target, template = map(Path, sys.argv[1:])
section = template.read_text()
if not target.exists():
    target.write_text(section)
else:
    original = target.read_bytes().decode("utf-8")
    heading = re.compile(r"(?m)^## Delegation policy[ \t]*\r?$")
    match = heading.search(original)
    if match:
        next_heading = re.search(r"(?m)^#{1,2}[ \t]+", original[match.end():])
        end = match.end() + next_heading.start() if next_heading else len(original)
        target.write_text(original[:match.start()] + section + original[end:])
    else:
        separator = "" if not original or original.endswith("\n\n") else "\n" if original.endswith("\n") else "\n\n"
        target.write_text(original + separator + section)
EOF
python3 - "$HOME/.omp/agent/mcp.json" "$SCRIPT_DIR/home/.omp/agent/mcp.json" <<'EOF'
import json, sys
from pathlib import Path
target, template = map(Path, sys.argv[1:])
old = json.loads(target.read_text()) if target.exists() else {}
new = json.loads(template.read_text())
old.setdefault("mcpServers", {}).update(new.get("mcpServers", {}))
target.write_text(json.dumps(old, indent=2) + "\n")
EOF
python3 - "$HOME/.omp/agent/lsp.json" "$SCRIPT_DIR/home/.omp/agent/lsp.json" "$LSP_BIN" <<'EOF'
import json, sys
from pathlib import Path
path, template, command = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
config = json.loads(path.read_text()) if path.exists() else {}
new = json.loads(template.read_text())
servers = config.setdefault("servers", {})
name, server = next(iter(new.get("servers", {}).items()))
existing = servers.setdefault(name, server.copy())
existing["command"] = command
existing["args"] = server["args"]
path.write_text(json.dumps(config, indent=2) + "\n")
EOF
