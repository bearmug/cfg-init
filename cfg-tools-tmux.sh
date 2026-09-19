#!/bin/bash
set -euo pipefail

# tmux + starter config + TPM plugin manager.
# Recipe (2026-09): installs TPM on first run (the old .tmux.conf references
# it but nothing installed it), copies home/.tmux.conf, installs plugins
# non-interactively. Re-run safe.

sudo apt-get update
sudo apt-get install -y tmux git

cp -f ./home/.tmux.conf "$HOME/.tmux.conf"

if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
	git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
else
	echo "TPM already installed, skipping clone"
fi

# Install/refresh plugins declared in .tmux.conf without attaching
"$HOME/.tmux/plugins/tpm/bin/install_plugins" || true

echo "### TMUX installation passed OK"
