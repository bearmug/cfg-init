#!/bin/bash
set -euo pipefail

# Docker CE + Compose plugin on Debian/Ubuntu.
# Recipe (2026-09): keyring under /etc/apt/keyrings with signed-by, arch from
# dpkg, codename from /etc/os-release; installs the Compose *plugin*
# (`docker compose`), not the standalone v2.23 binary. Replaces the old
# apt-key + hardcoded amd64 recipe.
# Re-run safe. Re-logon after first run so the `docker` group applies.
# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}" in
	ubuntu|debian)
		;;
	*)
		echo "This recipe supports Ubuntu and Debian only (detected: ${ID:-unknown})" >&2
		exit 1
		;;
esac
CODENAME="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
if [ -z "$CODENAME" ]; then
	echo "Could not determine the Debian/Ubuntu codename" >&2
	exit 1
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings

DOCKER_REPO="https://download.docker.com/linux/${ID}"
curl -fsSL "${DOCKER_REPO}/gpg" \
	| sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

ARCH="$(dpkg --print-architecture)"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] ${DOCKER_REPO} ${CODENAME} stable" \
	| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo groupadd -f docker
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

docker --version
docker compose version

echo "### DOCKER installation passed OK"
echo "Re-logon so the docker group applies (newgrp docker works in a pinch)."
