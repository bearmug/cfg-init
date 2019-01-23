#!/bin/bash

# ========================================================================
# erlang setup
# ========================================================================
sudo sh -c 'echo "deb https://packages.erlang-solutions.com/ubuntu xenial  contrib" >> /etc/apt/sources.list.d/erlang.list'
wget https://packages.erlang-solutions.com/ubuntu/erlang_solutions.asc
sudo apt-key add erlang_solutions.asc
sudo apt-get update
sudo apt-get install erlang -y

# ========================================================================
# have erlang CLI history
# ========================================================================
echo "export ERL_FLAGS=\"-kernel shell_history enabled\"" >> ~/.zshrc
source ~/.zshrc

echo "### ERLANG installation passed OK"