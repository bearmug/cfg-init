#!/bin/bash

# system performance monitoring
sudo apt-get install htop -y

# simplistic http tooling
sudo apt-get install curl wget -y

# database access clients
sudo apt install mysql-client postgresql-client  -y

# pip3 tooling
sudo apt-get install python3-pip

# install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.36.0/install.sh | bash

# extra tooling
sudo apt-get install awscli fzf -y

