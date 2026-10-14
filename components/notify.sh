# about: tg-notify: Telegram pings from any agent/shell (TG_BOT_TOKEN/TG_CHAT_ID)
. "$(dirname -- "$0")/../lib/cfg.sh"

need curl
put .local/bin/tg-notify 755
env_file="$HOME/.config/tg-notify/env"
if [ ! -f "$env_file" ] && [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ]; then
	mkdir -p "$(dirname "$env_file")"
	(umask 077; printf 'TG_BOT_TOKEN=%s\nTG_CHAT_ID=%s\n' "$TG_BOT_TOKEN" "$TG_CHAT_ID" > "$env_file")
	log "wrote $env_file"
fi
[ -f "$env_file" ] || warn "no credentials: rerun with TG_BOT_TOKEN=... TG_CHAT_ID=... or create $env_file (mode 600)"
