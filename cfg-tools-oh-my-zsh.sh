#!/bin/bash

# ========================================================================
# zsh setup
# ========================================================================
sudo apt-get update
sudo apt-get install zsh -y
chsh -s $(which zsh)

# ========================================================================
# oh-my-zsh setup
# ========================================================================
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

# ========================================================================
# zsh configure
# ========================================================================
sed -i "s/robbyrussell/avit/g" $HOME/.zshrc
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ~/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions
sed -i "s/(git)/(git zsh-syntax-highlighting zsh-autosuggestions)/g" $HOME/.zshrc

echo "### OH-MY-ZSH installation passed OK"
echo "please re-logon to apply changes"
echo "PLEASE RELOGON!!!"