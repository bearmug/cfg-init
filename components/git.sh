# about: git aliases + global ignore via include (keeps your ~/.gitconfig), identity, keychain
. "$(dirname -- "$0")/../lib/cfg.sh"

have git || pkg git
put .config/git/cfg-init.gitconfig
put .config/git/ignore

include="$HOME/.config/git/cfg-init.gitconfig"
git config --global --get-all include.path | grep -qxF "$include" \
	|| git config --global --add include.path "$include"
git config --global --get core.excludesFile >/dev/null \
	|| git config --global core.excludesFile "$HOME/.config/git/ignore"

# Identity: keep existing, else GIT_USER_NAME/GIT_USER_EMAIL, else prompt.
for field in name email; do
	git config --global --get "user.$field" >/dev/null && continue
	var="GIT_USER_$(echo "$field" | tr '[:lower:]' '[:upper:]')"
	value="${!var:-}"
	if [ -z "$value" ] && interactive; then
		read -r -p "  git user.$field: " value
	fi
	if [ -n "$value" ]; then
		git config --global "user.$field" "$value"
	else
		warn "user.$field unset: rerun with $var=..."
	fi
done
# OS credential store only; never plaintext `store`.
if ! git config --global --get credential.helper >/dev/null; then
	if is_mac; then
		git config --global credential.helper osxkeychain
	elif have git-credential-manager; then
		git config --global credential.helper manager
	fi
fi
log "git: $(git config --global user.name || echo '?') <$(git config --global user.email || echo '?')>"
