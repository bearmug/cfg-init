# about: zsh + Oh My Zsh + autosuggestions/syntax-highlighting; login shell (keeps a custom theme)
. "$(dirname -- "$0")/../lib/cfg.sh"

have zsh || pkg zsh
have git || pkg git
OMZ="${ZSH:-$HOME/.oh-my-zsh}"
if [ ! -d "$OMZ" ]; then
	RUNZSH=no CHSH=no KEEP_ZSHRC=yes \
		sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi
for plugin in zsh-autosuggestions zsh-syntax-highlighting; do
	dir="$OMZ/custom/plugins/$plugin"
	[ -d "$dir" ] || git clone -q --depth 1 "https://github.com/zsh-users/$plugin.git" "$dir"
done
[ -f "$HOME/.zshrc" ] || cp "$OMZ/templates/zshrc.zsh-template" "$HOME/.zshrc"
# syntax-highlighting must be the last plugin.
cfg zshrc "$HOME/.zshrc" pygmalion zsh-autosuggestions zsh-syntax-highlighting

zsh_path="$(command -v zsh)"
if [ "$(basename "${SHELL:-}")" != zsh ]; then
	if interactive; then
		chsh -s "$zsh_path" && log "login shell is zsh after re-login"
	else
		warn "login shell unchanged; run: chsh -s $zsh_path"
	fi
fi
