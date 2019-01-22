#!/bin/bash

# ========================================================================
# micro setup
# ========================================================================
sudo apt update
sudo apt install snapd -y
snap install micro --classic


echo "### MICRO installation passed OK"

echo "please re-logon to put micro on PATH"
echo "PLEASE RELOGON!!!"