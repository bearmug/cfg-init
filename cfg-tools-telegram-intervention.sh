#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 1 || -z "$1" ]]; then
    echo "Usage: $0 <harness-skill-directory>" >&2
    echo "Installs telegram-intervention beneath the supplied skill search path." >&2
    exit 1
fi
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
DEST="$1/telegram-intervention"
if [[ -e "$DEST" ]]; then
    BACKUP="${DEST}.backup.$(date +%Y%m%d%H%M%S).$$"
    cp -Rp "$DEST" "$BACKUP"
    echo "Existing skill backed up to $BACKUP"
fi
mkdir -p "$DEST/scripts"
cp "$ROOT_DIR/skills/telegram-intervention/SKILL.md" "$DEST/SKILL.md"
cp "$ROOT_DIR/skills/telegram-intervention/scripts/notify.py" "$DEST/scripts/notify.py"
echo "Installed skill at $DEST"
echo "Add its Harness integration rule to persistent agent instructions."
echo "Supply TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID through the harness secret environment."
echo "No secrets or harness configuration were installed."
