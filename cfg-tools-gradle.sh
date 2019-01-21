#!/bin/bash

# ========================================================================
# gradle setup
# ========================================================================
sudo apt-get remove gradle -y
sudo add-apt-repository ppa:cwchien/gradle -y
sudo apt-get update
sudo apt-get install gradle -y
sudo apt-get upgrade gradle -y

# ========================================================================
# gradle configure
# ========================================================================
cp -Rfu ./home/.gradle $HOME/

echo "### GRADLE installation passed OK"