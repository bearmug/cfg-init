#!/bin/bash
set -euo pipefail

# zsh + Oh My Zsh (canonical repo) with two bundled plugins.
# Recipe (2026-09): keeps the login shell switch, uses ohmyzsh/ohmyzsh
# (the robbyrussell org path now only redirects), runs the installer
# unattended, and appends plugins idempotently instead of sed-editing.
# Re-logon after first run to land in zsh. Re-run safe.

sudo apt-get update
sudo apt-get install -y zsh curl git

if [ ! -d "$HOME/.oh-my-zsh" ]; then
	RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
else
	echo "Oh My Zsh already installed at $HOME/.oh-my-zsh, skipping"
fi

for plugin in zsh-syntax-highlighting zsh-autosuggestions; do
	if [ ! -d "$HOME/.oh-my-zsh/custom/plugins/$plugin" ]; then
		git clone "https://github.com/zsh-users/$plugin.git" "$HOME/.oh-my-zsh/custom/plugins/$plugin"
	else
		echo "plugin $plugin already present, skipping"
	fi
done

# Idempotent: ensure the two plugins are listed, keep the pygmalion theme
python3 - "$HOME/.zshrc" <<'EOF'
import re, sys
path = sys.argv[1]
text = open(path).read()
text = re.sub(r'^ZSH_THEME="[^"]*".*$', 'ZSH_THEME="pygmalion"', text, flags=re.M)
m = re.search(r'^plugins=\(([^)]*)\)', text, flags=re.M)
if m:
    have = m.group(1).split()
    for p in ("zsh-syntax-highlighting", "zsh-autosuggestions"):
        if p not in have:
            have.append(p)
    text = text[:m.start(1)] + " ".join(have) + text[m.end(1):]
else:
    text += '\nplugins=(git zsh-syntax-highlighting zsh-autosuggestions)\n'
open(path, "w").write(text)
EOF

if [ "$SHELL" != "$(command -v zsh)" ]; then
	chsh -s "$(command -v zsh)"
	echo "Login shell switched to zsh — re-logon to apply."
else
	echo "Login shell already zsh."
fi

echo "### OH-MY-ZSH installation passed OK"
