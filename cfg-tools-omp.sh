#!/bin/bash

# ========================================================================
# OMP coding agent setup: tuned agent config + headroom MCP compression
# ========================================================================
uv tool install --python 3.13 "headroom-ai[all]"

# ========================================================================
# copy OMP agent configuration files to system locations
# (expects ~/.local/bin on PATH for the headroom MCP server)
# ========================================================================
mkdir -p $HOME/.omp/agent
cp -f ./home/.omp/agent/config.yml $HOME/.omp/agent/config.yml
cp -f ./home/.omp/agent/mcp.json $HOME/.omp/agent/mcp.json

echo "### OMP installation passed OK"
