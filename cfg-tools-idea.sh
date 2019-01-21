#!/bin/bash

# ========================================================================
# idea setup
# ========================================================================
sudo add-apt-repository ppa:mmk2410/intellij-idea-community -y
sudo apt-get update
sudo apt-get install intellij-idea-community -y
sudo apt-get upgrade gradle -y


echo "### IDEA installation passed OK"