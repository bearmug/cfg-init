#!/bin/bash
set -euo pipefail

# Gradle via SDKMAN (user scope, current major line) + shared daemon config.
# Recipe (2026-09): replaces the retired cwchien/gradle PPA (last published
# for Ubuntu mantic / Gradle 8.3). Installs SDKMAN if missing, installs the
# default SDKMAN gradle, and leaves version switches to `sdk list gradle`.
# Copies home/.gradle/gradle.properties (daemon, parallel, configure-on-demand).
# Re-run safe.

if [ ! -d "$HOME/.sdkman" ]; then
	curl -s "https://get.sdkman.io" | bash
fi

# shellcheck disable=SC1091
source "$HOME/.sdkman/bin/sdkman-init.sh"

if sdk current gradle >/dev/null 2>&1; then
	echo "Gradle is already installed through SDKMAN"
else
	sdk install gradle
fi
gradle --version

mkdir -p "$HOME/.gradle"
cp -Rf ./home/.gradle/. "$HOME/.gradle/"

echo "### GRADLE installation passed OK"
echo "Switch versions with: sdk list gradle && sdk install gradle <version> && sdk default gradle <version>"
