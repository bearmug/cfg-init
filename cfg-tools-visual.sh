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

# ========================================================================
# install multitouch gestures support
# ========================================================================
sudo gpasswd -a $USER input
sudo apt install xdotool libinput-tools
cd /tmp
git clone http://github.com/bulletmark/libinput-gestures
cd libinput-gestures
sudo ./libinput-gestures-setup install

cp home/libinput-gestures.conf ~/.config/libinput-gestures.conf

libinput-gestures-setup start
libinput-gestures-setup autostart

echo "### visual enhancements are in place, please RESTART!"