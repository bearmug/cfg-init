#!/bin/bash

# ========================================================================
# f.lux setup
# ========================================================================
sudo add-apt-repository ppa:nathan-renniewaldock/flux -y
sudo apt-get update
sudo apt-get install fluxgui -y
fluxgui &

echo "### now your eyes going to feel better!"