#!/bin/bash

# setup custom PPA
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo add-apt-repository ppa:cwchien/gradle -y

# update system
sudo apt-get update -y

# install git, openjdk, gradle
sudo apt-get -y install nginx git openjdk-8-jdk gradle-2.12

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
