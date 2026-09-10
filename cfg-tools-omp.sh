#!/bin/bash

# ========================================================================
# OMP coding agent setup: token-spend tuning + headroom MCP compression.
# Applies per-key so existing providers/models on the machine are kept.
# Spend keys mirror home/.omp/agent/config.yml - keep both in sync.
# ========================================================================
uv tool install --python 3.13 "headroom-ai[all]"

# ------------------------------------------------------------------------
# spend tuning (merge-safe: one key at a time, no file clobbering)
# ------------------------------------------------------------------------
omp config set compaction.thresholdTokens 280000
omp config set compaction.thresholdPercent -- -1
omp config set compaction.keepRecentTokens 20000
omp config set compaction.idleEnabled true
omp config set compaction.idleThresholdTokens 200000
omp config set compaction.idleTimeoutSeconds 180
omp config set compaction.v2RetainedMessageBudget 32000
omp config set display.showTokenUsage true
omp config set display.cacheMissMarker true
omp config set snapcompact.toolResults true
omp config set advisor.maxNotesPerUpdate 1

# ------------------------------------------------------------------------
# headroom MCP server (expects ~/.local/bin on PATH); merge, don't clobber
# ------------------------------------------------------------------------
mkdir -p $HOME/.omp/agent
if [ -f $HOME/.omp/agent/mcp.json ]; then
python3 - "$HOME/.omp/agent/mcp.json" ./home/.omp/agent/mcp.json <<'EOF'
import json, sys
old = json.load(open(sys.argv[1]))
new = json.load(open(sys.argv[2]))
old.setdefault("mcpServers", {}).update(new.get("mcpServers", {}))
json.dump(old, open(sys.argv[1], "w"), indent=2)
EOF
else
cp -f ./home/.omp/agent/mcp.json $HOME/.omp/agent/mcp.json
fi

echo "### OMP installation passed OK"
