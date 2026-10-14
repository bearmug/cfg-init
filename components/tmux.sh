# about: tmux config (C-a prefix, Alt-arrows) + TPM plugins
. "$(dirname -- "$0")/../lib/cfg.sh"

have tmux || pkg tmux
put .tmux.conf
TPM="$HOME/.tmux/plugins/tpm"
[ -d "$TPM" ] || git clone -q --depth 1 https://github.com/tmux-plugins/tpm "$TPM"
"$TPM/bin/install_plugins" >/dev/null || warn "TPM plugin install failed; press prefix+I inside tmux"
