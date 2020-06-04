#!/bin/bash

# fix display resolution at Ubuntu

# create new resolution mode
sudo cvt 1920 1080 60

# declare new resolution
sudo xrandr --newmode "1920x1080_60.00" 173.00 1920 2048 2248 2576 1080 1083 1088 1120 -hsync +vsync

# determine name of display
sudo xrandr -q

# add new resolution mode to display device
sudo xrandr --addmode Virtual1 1920x1080_60.00
