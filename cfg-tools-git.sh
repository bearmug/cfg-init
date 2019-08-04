#!/bin/bash

# ========================================================================
# git setup
# ========================================================================
sudo apt-get -y install git

# ========================================================================
# copy git configuration files to system locations
# ========================================================================
cp -f ./home/.gitconfig $HOME/.gitconfig
cp -f ./home/.gitignore-file $HOME/.gitignore

# ========================================================================
# alter username and email for git user
# ========================================================================
echo "### please input git user name"
read GIT_USER_NAME
echo "please input gituser email"
read GIT_USER_EMAIL

sed -i "s/git-user-name/${GIT_USER_NAME}/g" $HOME/.gitconfig
sed -i "s/git-user-email/${GIT_USER_EMAIL}/g" $HOME/.gitconfig

echo "### GIT installation passed OK"
