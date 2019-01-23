#!/bin/bash

# ========================================================================
# f.lux setup
# ========================================================================
sudo add-apt-repository ppa:nathan-renniewaldock/flux
sudo apt-get update
sudo apt-get install fluxgui -y
fluxgui &

# ========================================================================
# clipboard setup
# ========================================================================
sudo apt-get install xclip -y

echo "### now your eyes going to feel better!"