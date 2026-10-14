#!/usr/bin/env bash
# cfg-init: idempotent workstation setup for macOS and Debian/Ubuntu.
# Usage: ./install.sh                interactive picker
#        ./install.sh --yes [NAME..] non-interactive (no NAME = defaults)
#        ./install.sh list | check
set -euo pipefail
. "$(dirname -- "${BASH_SOURCE[0]}")/lib/cfg.sh"

# Order matters: later components use tools/files from earlier ones.
ALL="packages git zsh tmux omp feedback t3 notify gate"
DEFAULTS="packages git zsh tmux omp feedback t3 notify"

about() { sed -n 's/^# about: //p' "$ROOT/components/$1.sh"; }

list() {
	for c in $ALL; do
		case " $DEFAULTS " in *" $c "*) mark='*' ;; *) mark=' ' ;; esac
		printf '%s %-9s %s\n' "$mark" "$c" "$(about "$c")"
	done
	echo '(* = default)'
}

case "${1:-}" in
	-h|--help) sed -n '2,5p' "$0" | sed 's/^# //'; exit 0 ;;
	list) list; exit 0 ;;
	check) exec bash "$ROOT/lib/check.sh" ;;
	--yes|-y) export CFG_YES=1; shift ;;
esac

selected="$*"
if [ -z "$selected" ]; then
	if interactive; then
		list
		printf '\nComponents [Enter = defaults, "all", or names]: '
		read -r selected
	elif [ "${CFG_YES:-0}" != 1 ]; then
		die "no terminal: pass --yes [NAME..] (see: ./install.sh list)"
	fi
	[ -n "$selected" ] || selected="$DEFAULTS"
fi
[ "$selected" != all ] || selected="$ALL"
for c in $selected; do
	[ -f "$ROOT/components/$c.sh" ] || die "unknown component '$c' (see: ./install.sh list)"
done

failed=""
for c in $ALL; do
	case " $selected " in *" $c "*) ;; *) continue ;; esac
	printf '\n==> %s: %s\n' "$c" "$(about "$c")"
	bash "$ROOT/components/$c.sh" || failed="$failed $c"
done

echo
if [ -n "$failed" ]; then
	echo "FAILED:$failed"
	exit 1
fi
echo "OK: $selected. Verify with ./install.sh check"
