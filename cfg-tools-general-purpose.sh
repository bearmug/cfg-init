#!/bin/bash
set -euo pipefail

# Baseline CLI comfort on Debian/Ubuntu: monitor, fetch, DB clients, jq/fzf.
# Recipe (2026-09): one apt pass, `-y` everywhere; nvm pinned to v0.40.7.
# Node itself stays out (per-user via nvm). Re-run safe.

sudo apt-get update
sudo apt-get install -y \
	htop \
	curl wget \
	mysql-client postgresql-client \
	python3-pip \
	jq fzf

# nvm is per-user; keep it pinned and idempotent
if [ ! -d "$HOME/.nvm" ]; then
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.7/install.sh | bash
else
	echo "nvm already installed at $HOME/.nvm, skipping"
fi

echo "### GENERAL-PURPOSE tooling installation passed OK"
