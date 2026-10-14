# Sourced by install.sh and components. Bash 3.2-compatible (stock macOS).
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_SRC="$ROOT/home"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

log() { printf '  %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }
die() { printf '  x %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
need() { have "$1" || die "$1 is required${2:+: $2}"; }
is_mac() { [ "$(uname -s)" = Darwin ]; }
interactive() { [ -t 0 ] && [ -t 1 ] && [ "${CFG_YES:-0}" != 1 ]; }

# cfg <command> ...: see lib/cfg.py
cfg() { python3 "$ROOT/lib/cfg.py" "$@"; }
# put <repo path under home/> [mode]: install to the same path under $HOME
put() { cfg put "$HOME_SRC/$1" "$HOME/$1" ${2:+"$2"}; }

# pkg <name>...: install missing OS packages (Homebrew on macOS, apt on Debian/Ubuntu)
pkg() {
	if is_mac; then
		need brew "install Homebrew from https://brew.sh"
		brew install "$@"
	elif have apt-get; then
		sudo apt-get update -qq
		sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@"
	else
		die "unsupported OS: install $* manually"
	fi
}
