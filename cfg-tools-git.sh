#!/bin/bash
set -euo pipefail

# Git + starter config. Installs Git, configures a portable global ignore file,
 # and fills identity from environment or an interactive prompt.
 # Pass --no-prompt for non-interactive runs (env must supply both values).
 # Existing config files are backed up with a timestamp suffix; re-runs are safe.

NO_PROMPT=0
if [ "${1:-}" = "--no-prompt" ]; then
	NO_PROMPT=1
fi

sudo apt-get update
sudo apt-get install -y git

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
GIT_CONFIG_DIR="$CONFIG_HOME/git"
mkdir -p "$GIT_CONFIG_DIR"

backup_if_present() {
	local path="$1"
	if [ -e "$path" ]; then
		cp -f "$path" "$path.bak-$(date +%Y%m%d%H%M%S)"
	fi
}


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
if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
	echo "Git identity must include a non-empty name and email" >&2
	exit 1
fi
backup_if_present "$HOME/.gitconfig"
backup_if_present "$GIT_CONFIG_DIR/ignore"
cp -f ./home/.gitconfig "$HOME/.gitconfig"
cp -f ./home/.config/git/ignore "$GIT_CONFIG_DIR/ignore"

git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
git config --global core.excludesFile "$GIT_CONFIG_DIR/ignore"

# Use a native credential manager only when it is available; otherwise Git
# retains its normal prompting behavior without writing credentials to disk.
if command -v git-credential-osxkeychain >/dev/null 2>&1; then
	git config --global credential.helper osxkeychain
elif command -v git-credential-manager >/dev/null 2>&1; then
	git config --global credential.helper manager
elif command -v git-credential-manager-core >/dev/null 2>&1; then
	git config --global credential.helper manager-core
fi

echo "### GIT installation passed OK"
