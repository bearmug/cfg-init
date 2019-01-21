#!/bin/bash

# ========================================================================
# purge packages and install docker ce
# ========================================================================
sudo apt-get remove docker docker-engine docker.io containerd runc -y
sudo apt-get update
# https://docs.docker.com/install/linux/docker-ce/ubuntu/
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu xenial stable"
sudo apt-get update
sudo apt-get install docker-ce -y


# ========================================================================
# install docker-compose
# ========================================================================
# https://docs.docker.com/compose/install/
sudo curl -L https://github.com/docker/compose/releases/download/1.20.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

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
