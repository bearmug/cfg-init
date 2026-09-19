#!/bin/bash
set -euo pipefail

# Git + starter config. Copies home/.gitconfig and home/.gitignore-file,
# then fills the user placeholders. Env overrides beat prompts:
#   GIT_USER_NAME="Jane" GIT_USER_EMAIL="jane@example.com" ./cfg-tools-git.sh
# Pass `--no-prompt` for non-interactive runs (env must supply both values).
# The copies back up any existing files with a timestamp suffix. Re-run safe.

NO_PROMPT=0
if [ "${1:-}" = "--no-prompt" ]; then
	NO_PROMPT=1
fi

sudo apt-get update
sudo apt-get install -y git

for f in .gitconfig .gitignore; do
	if [ -e "$HOME/$f" ]; then
		cp -f "$HOME/$f" "$HOME/$f.bak-$(date +%Y%m%d%H%M%S)"
	fi
done
cp -f ./home/.gitconfig "$HOME/.gitconfig"
cp -f ./home/.gitignore-file "$HOME/.gitignore"

GIT_USER_NAME="${GIT_USER_NAME:-}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-}"

if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
	if [ "$NO_PROMPT" = "1" ]; then
		echo "GIT_USER_NAME and GIT_USER_EMAIL must be set with --no-prompt" >&2
		exit 1
	fi
	read -r -p "git user name: " GIT_USER_NAME
	read -r -p "git user email: " GIT_USER_EMAIL
fi

# git-config handles escaping; no sed placeholder surgery
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"

echo "### GIT installation passed OK"
