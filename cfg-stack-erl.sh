#!/bin/bash

# ========================================================================
# download and install kerl
# ========================================================================
mkdir -p ~/.bin
cd ~/.bin
curl -O https://raw.githubusercontent.com/kerl/kerl/master/kerl
chmod a+x kerl
echo "export PATH=$HOME/.bin:$PATH" >> ~/.zshrc
source ~/.zshrc

# ========================================================================
# build OTP 21
# ========================================================================
sudo apt-get install -y libssl-dev automake autoconf libncurses5-dev
kerl build 21.3
kerl install 21.3 ~/kerl/21.3

# ========================================================================
# activate OTP 21 on logon
# ========================================================================
. /home/pavel/kerl/21.3/activate
echo ". /home/pavel/kerl/21.3/activate" >> ~/.zshrc

echo "### Kerl ERLANG installation passed OK"