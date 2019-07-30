#!/bin/bash

# ========================================================================
# proper fonts setup
# ========================================================================
curl -L https://github.com/hbin/top-programming-fonts/raw/master/install.sh | bash
echo "Linux-like systems recommended fonts setup:"
echo "Settings -> Editor -> Font -> Menlo"
echo "Settings -> Appearance & Behavior -> Appearance -> Use custom font -> Noto Sans"

# ========================================================================
# Intellij Toolbox page open
# ========================================================================
xdg-open https://www.jetbrains.com/toolbox/app/

echo "### Intellij Toolbox page open OK"
echo "### Remember to put jetbrains-toolbox binary to relevant path before use"