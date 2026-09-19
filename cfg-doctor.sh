#!/bin/bash
set -u
set -o pipefail

# Read-only health report for cfg-init and optional local model services.
# Optional endpoint checks are enabled with CFG_INIT_CHECK_LOCAL_AI=1.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
failures=0
warnings=0

ok() {
	printf 'OK    %s\n' "$1"
}
warn() {
	printf 'WARN  %s\n' "$1"
	warnings=$((warnings + 1))
}
fail() {
	printf 'FAIL  %s\n' "$1"
	failures=$((failures + 1))
}

section() {
	printf '\n[%s]\n' "$1"
}

check_command() {
	local command_name="$1" required="${2:-0}"
	if command -v "$command_name" >/dev/null 2>&1; then
		ok "$command_name available"
	elif [ "$required" = 1 ]; then
		fail "$command_name missing"
	else
		warn "$command_name missing (optional)"
	fi
}

check_url() {
	local label="$1" url="$2"
	if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
		ok "$label reachable"
	else
		warn "$label unavailable"
	fi
}

check_json() {
	local file="$1"
	if [ ! -f "$file" ]; then
		warn "$(basename "$file") not installed"
		return
	fi
	if command -v python3 >/dev/null 2>&1 \
		&& python3 - "$file" <<'PY' >/dev/null 2>&1
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    json.load(stream)
PY
	then
		ok "$(basename "$file") is valid JSON"
	else
		fail "$(basename "$file") is invalid JSON"
	fi
}

section "system"
ok "OS: $(uname -s) / $(uname -m)"
if [ "$(uname -s)" = "Darwin" ]; then
	check_command brew 1
	if [ "$(uname -m)" = "arm64" ]; then
		ok "Apple Silicon architecture"
	else
		warn "non-Apple-Silicon macOS architecture"
	fi
else
	warn "recipes are primarily Debian/Ubuntu or macOS"
fi

section "commands"
check_command git 1
check_command curl 1
check_command jq
check_command fzf
check_command tmux
check_command uv
check_command bun
check_command omp
check_command docker

section "git safety"
if command -v git >/dev/null 2>&1; then
	credential_helper="$(git config --global --get credential.helper 2>/dev/null || true)"
	if [ "$credential_helper" = "store" ]; then
		fail "Git plaintext credential store is enabled"
	else
		ok "Git plaintext credential store is not enabled"
	fi
	if git config --global --get core.excludesFile >/dev/null 2>&1; then
		ok "Git global excludes file is configured"
	else
		warn "Git global excludes file is not configured"
	fi
fi

section "OMP"
OMP_DIR="${OMP_CONFIG_DIR:-$HOME/.omp/agent}"
if [ -f "$OMP_DIR/config.yml" ]; then
	ok "OMP config present"
else
	warn "OMP config not installed"
fi
if [ -f "$OMP_DIR/models.yml" ]; then
	ok "OMP model registry present"
else
	warn "OMP model registry not installed"
fi
check_json "$OMP_DIR/mcp.json"

section "local model services"
check_url "model gate" "${MODEL_GATE_HEALTH_URL:-http://127.0.0.1:8090/health}"
if [ "${CFG_INIT_CHECK_LOCAL_AI:-0}" = 1 ]; then
	check_url "llama.cpp" "${LLAMA_CPP_MODELS_URL:-http://127.0.0.1:8005/v1/models}"
	check_url "MLX" "${MLX_MODELS_URL:-http://127.0.0.1:8010/v1/models}"
	check_url "Ollama" "${OLLAMA_TAGS_URL:-http://127.0.0.1:11434/api/tags}"
else
	warn "additional local-AI checks skipped; set CFG_INIT_CHECK_LOCAL_AI=1 to enable"
fi

section "repository"
for file in \
	"$ROOT_DIR/home/.gitconfig" \
	"$ROOT_DIR/home/.config/git/ignore" \
	"$ROOT_DIR/home/.omp/agent/config.yml" \
	"$ROOT_DIR/home/.omp/agent/mcp.json" \
	"$ROOT_DIR/home/.omp/agent/config.local.example.yml" \
	"$ROOT_DIR/home/.omp/agent/models.local.example.yml"; do
	if [ -f "$file" ]; then
		ok "repository template $(basename "$file") present"
	else
		warn "repository template $(basename "$file") missing"
	fi
done

printf '\nSummary: %d failure(s), %d warning(s)\n' "$failures" "$warnings"
if [ "$failures" -gt 0 ]; then
	exit 1
fi
