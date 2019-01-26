#!/bin/bash

# ========================================================================
# idea setup
# ========================================================================
sudo add-apt-repository ppa:mmk2410/intellij-idea-community -y
sudo apt-get update
sudo apt-get install intellij-idea-community -y
sudo apt-get upgrade gradle -y

# ========================================================================
# proper fonts setup
# ========================================================================
curl -L https://github.com/hbin/top-programming-fonts/raw/master/install.sh | bash

echo "Linux-like systems recommended fonts setup:"
echo "Settings -> Editor -> Font -> Menlo"
echo "Settings -> Appearance & Behavior -> Appearance -> Use custom font -> Noto Sans"

echo "### IDEA installation passed OK"