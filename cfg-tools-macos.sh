#!/bin/bash
set -euo pipefail

# macOS workstation recipe. Homebrew must already be installed; use the
# official Homebrew installer separately rather than piping an installer here.
# Set CFG_INIT_LOCAL_AI=1 to add optional Ollama and llama.cpp packages.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(uname -s)" != "Darwin" ]; then
	echo "cfg-tools-macos.sh requires macOS" >&2
	exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
	echo "Homebrew is required; install it from https://brew.sh/ and rerun" >&2
	exit 1
fi

brew bundle --file="$ROOT_DIR/Brewfile"

if [ "${CFG_INIT_LOCAL_AI:-0}" = 1 ]; then
	brew bundle --file="$ROOT_DIR/Brewfile.local-ai"
else
	echo "Skipping optional local-AI backends; set CFG_INIT_LOCAL_AI=1 to enable"
fi

echo "### macOS tooling installation passed OK"
