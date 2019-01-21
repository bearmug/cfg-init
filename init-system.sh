#!/bin/bash

# ========================================================================
# initial system update
# ========================================================================
# update system
sudo apt-get update -y
sudo apt-get upgrade


# ========================================================================
# install xfce4 desktop and Idea
# ========================================================================
sudo apt-get -y install -y ubuntu-desktop xfce4 xfce4-goodies xrdp
sudo sed -i -- 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sudo passwd ubuntu

# make xfce4 session default
echo xfce4-session > ~/.xsession
sudo cp /home/ubuntu/.xsession /etc/skel

sudo service ssh restart
sudo service xrdp restart
