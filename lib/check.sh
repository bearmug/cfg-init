#!/usr/bin/env bash
# Read-only health check. Lines: `ok|warn|FAIL <area>: <detail>`; exits 1 on FAIL.
. "$(dirname -- "${BASH_SOURCE[0]}")/cfg.sh"
set +e
fails=0 warns=0
ok() { printf 'ok   %s\n' "$*"; }
w() { printf 'warn %s\n' "$*"; warns=$((warns + 1)); }
bad() { printf 'FAIL %s\n' "$*"; fails=$((fails + 1)); }
installed() { [ -e "$HOME/$1" ]; }
# Installed payloads that differ from the repo mean a component should be re-run.
drift() {
	local area="$1" path
	shift
	for path in "$@"; do
		if ! installed "$path"; then w "$area: $path not installed"
		elif ! cmp -s "$HOME_SRC/$path" "$HOME/$path"; then w "$area: ~/$path differs from repo (re-run: ./install.sh --yes $area)"
		fi
	done
}

missing=""
for c in git gh jq fzf rg fd btop tmux direnv uv bun omp zsh python3 curl; do
	have "$c" || missing="$missing $c"
done
[ -z "$missing" ] && ok "packages: all present" || w "packages: missing$missing"

if have git; then
	git config --global --get-all include.path | grep -q cfg-init.gitconfig && ok "git: aliases included" || w "git: aliases not included"
	case "$(git config --global --get-all credential.helper)" in store*) bad "git: plaintext credential store enabled (fix: ./install.sh --yes git)" ;; *) ok "git: no plaintext credentials" ;; esac
	git config --global user.email >/dev/null && ok "git: identity set" || w "git: user.email unset"
	drift git .config/git/cfg-init.gitconfig .config/git/ignore
fi

[ -d "${ZSH:-$HOME/.oh-my-zsh}" ] && ok "zsh: oh-my-zsh present" || w "zsh: oh-my-zsh missing"
[ "$(basename "${SHELL:-}")" = zsh ] && ok "zsh: login shell" || w "zsh: login shell is ${SHELL:-unset}"

[ -d "$HOME/.tmux/plugins/tpm" ] && ok "tmux: TPM present" || w "tmux: TPM missing"
drift tmux .tmux.conf

if have omp; then
	agent="$(omp config path 2>/dev/null)"
	judge="$(omp config get modelRoles --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["value"].get("judge",""))' 2>/dev/null)"
	case "$judge" in typesafe/jev-latest) ok "omp: judge is native Jev" ;; *) w "omp: judge is '${judge:-unset}', not typesafe/jev-latest" ;; esac
	have typescript-language-server && ok "omp: TypeScript LSP present" || w "omp: typescript-language-server missing"
	grep -q '^## Delegation policy' "$agent/APPEND_SYSTEM.md" 2>/dev/null && ok "omp: delegation policy present" || w "omp: delegation policy missing"
else
	w "omp: not installed"
fi

if installed .agents/skills/dissatisfaction/feedback.py; then
	drift feedback .agents/skills/dissatisfaction/feedback.py .agents/skills/dissatisfaction/SKILL.md \
		.local/share/cfg-init-feedback/screen_omp.py .omp/agent/extensions/dissatisfaction.ts
	url="$(python3 -c 'import json,os; print(json.load(open(os.path.expanduser("~/.config/cfg-init-feedback/config.json")))["FEEDBACK_MODEL_URL"])' 2>/dev/null)"
	curl -fsS --max-time 3 "${url:-http://127.0.0.1:8086/v1}/models" >/dev/null 2>&1 \
		&& ok "feedback: scorer reachable at ${url}" || bad "feedback: scorer unreachable at ${url:-unset}"
	failed="$(python3 "$HOME/.agents/skills/dissatisfaction/feedback.py" status 2>/dev/null \
		| python3 -c 'import json,sys; print(sum(e.get("state")=="failed" for e in json.load(sys.stdin).get("events",[])))' 2>/dev/null)"
	[ "${failed:-0}" = 0 ] && ok "feedback: no failed events" || w "feedback: $failed failed events (feedback.py status)"
else
	w "feedback: not installed"
fi

if [ -x "$HOME/.local/bin/omp-feedback" ]; then
	ok "t3: launcher ~/.local/bin/omp-feedback"
	drift t3 .local/share/cfg-init-feedback/omp_acp.py .local/share/cfg-init-feedback/t3_policy.py \
		.omp/agent/extensions/t3-coordinator.ts .omp/agent/t3.yml
else
	w "t3: omp-feedback launcher not installed"
fi

if have tg-notify; then
	[ -f "$HOME/.config/tg-notify/env" ] && ok "notify: tg-notify configured" || w "notify: ~/.config/tg-notify/env missing"
else
	w "notify: tg-notify not installed"
fi

if installed .local/share/model-gate/model-gate-proxy.mjs; then
	curl -fsS --max-time 3 "http://127.0.0.1:${MODEL_GATE_PORT:-8090}/health" >/dev/null 2>&1 \
		&& ok "gate: healthy" || w "gate: installed but not running"
fi

printf '\n%d failure(s), %d warning(s)\n' "$fails" "$warns"
[ "$fails" = 0 ]
