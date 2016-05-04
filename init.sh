#!/bin/bash

# ========================================================================
# initial system update
# ========================================================================
# setup custom PPA
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo add-apt-repository ppa:cwchien/gradle -y
sudo add-apt-repository ppa:mmk2410/intellij-idea-community -y

# update system
sudo apt-get update -y


# ========================================================================
# install xfce4 desktop and Idea
# ========================================================================
sudo apt-get -y install -y ubuntu-desktop xfce4 xfce4-goodies xrdp intellij-idea-community
sudo sed -i -- 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sudo passwd ubuntu

# make xfce4 session default
echo xfce4-session > ~/.xsession
sudo cp /home/ubuntu/.xsession /etc/skel

sudo service ssh restart
sudo service xrdp restart

# ========================================================================
# toolchain setup
# ========================================================================
# install git, openjdk, gradle
sudo apt-get -y install nginx git openjdk-8-jdk gradle-2.12
# fix ccacerts Ubuntu issue
sudo dpkg --purge --force-depends ca-certificates-java
sudo apt-get install ca-certificates-java


# link nginx web-root to /var/www Apache location and ~/Web alias
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.bak
sudo mkdir /var/www
ln -s /var/www $HOME/Web
sudo chmod 777 /var/www
sudo sed -i -- 's/\/usr\/share\/nginx\/html/\/var\/www/g' /etc/nginx/sites-available/default
service nginx start


# clone any github repo rightaway
git clone https://github.com/bearmug/config-common.git ~/config-common
git clone https://github.com/bearmug/portfolio-bench.git ~/portfolio-bench

# copy git and gradle configuration files to system locations
cp -Rfu ./home/.g* $HOME/
