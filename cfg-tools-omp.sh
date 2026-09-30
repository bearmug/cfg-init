#!/bin/bash

# Tune OMP without replacing unrelated user configuration.
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Install the local context-compression tool and TypeScript LSP prerequisites.
uv tool install --python 3.13 "headroom-ai[all]"
bun install -g typescript typescript-language-server@6.0.1
LSP_BIN="$(command -v typescript-language-server)"

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

mkdir -p "$HOME/.omp/agent"
python3 - "$HOME/.omp/agent" "$SCRIPT_DIR/home/.omp/agent" "$LSP_BIN" <<'EOF'
import json, re, subprocess, sys
from pathlib import Path

target_dir, template_dir = map(Path, sys.argv[1:3])
lsp_command = sys.argv[3]

for key, judge in (("modelRoles", "typesafe/jev-latest"),
                   ("retry.fallbackChains", ["opencode-zen-jev/jev-1.13"])):
    record = json.loads(subprocess.check_output(
        ["omp", "config", "get", key, "--json"], text=True
    ))["value"]
    record["judge"] = judge
    subprocess.run(["omp", "config", "set", key, json.dumps(record)], check=True)

path = target_dir / "APPEND_SYSTEM.md"
section = (template_dir / path.name).read_text()
original = path.read_bytes().decode("utf-8") if path.exists() else ""
match = re.search(r"(?m)^## Delegation policy[ \t]*\r?$", original)
if match:
    next_heading = re.search(r"(?m)^#{1,2}[ \t]+", original[match.end():])
    end = match.end() + next_heading.start() if next_heading else len(original)
    updated = original[:match.start()] + section + original[end:]
else:
    separator = "" if not original or original.endswith("\n\n") else "\n" if original.endswith("\n") else "\n\n"
    updated = original + separator + section
path.write_text(updated)

path = target_dir / "mcp.json"
config = json.loads(path.read_text()) if path.exists() else {}
template = json.loads((template_dir / path.name).read_text())
config.setdefault("mcpServers", {}).update(template["mcpServers"])
path.write_text(json.dumps(config, indent=2) + "\n")

path = target_dir / "lsp.json"
config = json.loads(path.read_text()) if path.exists() else {}
template = json.loads((template_dir / path.name).read_text())
server = template["servers"]["typescript-language-server"]
existing = config.setdefault("servers", {}).setdefault("typescript-language-server", server.copy())
existing.update(command=lsp_command, args=server["args"])
path.write_text(json.dumps(config, indent=2) + "\n")
EOF
