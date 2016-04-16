#!/bin/bash

# setup custom PPA
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo add-apt-repository ppa:cwchien/gradle -y

# update system
sudo apt-get update -y

# install git, openjdk, gradle
sudo apt-get -y install git openjdk-8-jdk gradle-2.12

# copy git and gradle configuration files to system locations
cp -Rfu .gradle ~/
cp -fu .gitignore ~/
cp -fu .gitconfig ~/

# clone any github repo rightaway
git clone https://github.com/bearmug/portfolio-bench.git