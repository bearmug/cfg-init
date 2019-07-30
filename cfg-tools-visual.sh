#!/bin/bash

# ========================================================================
# plasma kubuntu desktop setup
# ========================================================================
sudo apt install tasksel
sudo tasksel install kubuntu-desktop

# ========================================================================
# turn redshift on autostart
# ========================================================================
cp ./home/redshift.desktop ~/.config/autostart/redshift.desktop

echo "### now your eyes going to feel better!"