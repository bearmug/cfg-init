# about: CLI baseline: git gh jq fzf ripgrep fd btop tmux direnv zsh uv bun omp
. "$(dirname -- "$0")/../lib/cfg.sh"

if is_mac; then
	need brew "install Homebrew from https://brew.sh"
	brew bundle --file="$ROOT/Brewfile"
	exit 0
fi

need apt-get "Linux support is Debian/Ubuntu only"
pkg git curl unzip python3 jq fzf ripgrep fd-find btop tmux direnv zsh
pkg gh || warn "gh is not in this distro's apt; see https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
mkdir -p "$HOME/.local/bin"
# Debian names fd `fdfind`.
have fd || ln -sf "$(command -v fdfind)" "$HOME/.local/bin/fd"
have uv || curl -LsSf https://astral.sh/uv/install.sh | sh
have bun || curl -fsSL https://bun.sh/install | bash
have omp || curl -fsSL https://omp.sh/install | sh
