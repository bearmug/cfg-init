#!/bin/bash

# ========================================================================
# purge packages and prepare system
# ========================================================================
sudo apt-get remove docker docker-engine docker.io containerd runc -y
sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common -y

# ========================================================================
# add Docker GPG key
# ========================================================================
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# ========================================================================
# add stable Docker repository
# ========================================================================
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

# ========================================================================
# install Docker CE
# ========================================================================
sudo apt-get update
sudo apt-get install docker-ce -y

# ========================================================================
# create docker usergroup and configure it
# ========================================================================
sudo groupadd docker
sudo usermod -aG docker $USER

# ========================================================================
# start docker on system boot
# ========================================================================
sudo systemctl enable docker

echo "### DOCKER installation passed OK"

echo "please re-logon to configure docker running without sudo"
echo "PLEASE RELOGON!!!"
