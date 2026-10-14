# about: dissatisfaction feedback loop: skill, OMP extension, screening, local scorer (MLX on macOS)
. "$(dirname -- "$0")/../lib/cfg.sh"

need python3
need omp "run the packages component first"
skill=.agents/skills/dissatisfaction
for file in "$HOME_SRC/$skill"/*; do
	case "$(basename "$file")" in test_*|__pycache__) continue ;; esac
	put "$skill/$(basename "$file")"
done
put .local/share/cfg-init-feedback/screen_omp.py
put .omp/agent/extensions/dissatisfaction.ts

python="$(command -v python3)"
notify=''
is_mac && notify='["/usr/bin/osascript","-e","on run argv\n display notification (item 1 of argv) with title \"Assistant feedback\"\nend run"]'
cfg defaults "$HOME/.config/cfg-init-feedback/config.json" \
	FEEDBACK_PYTHON="$python" \
	FEEDBACK_OMP_BIN="$(command -v omp)" \
	FEEDBACK_MODEL_URL=http://127.0.0.1:8086/v1 \
	FEEDBACK_MODEL=mlx-community/Qwen3-1.7B-4bit \
	FEEDBACK_SCREEN_COMMAND="[\"$python\",\"$HOME/.local/share/cfg-init-feedback/screen_omp.py\"]" \
	FEEDBACK_SCREEN_MODEL=openai-codex/gpt-6-luna \
	FEEDBACK_IMPLEMENT_MODEL=openai-codex/gpt-6.1-sol \
	FEEDBACK_SCREEN_TIMEOUT=660 \
	FEEDBACK_NOTIFY_COMMAND="$notify"
if [ "${FEEDBACK_SKIP_MODEL:-0}" = 1 ] || ! is_mac; then
	log "local scorer not managed here: serve an OpenAI-compatible model with logprobs at FEEDBACK_MODEL_URL"
	exit 0
fi
have mlx_lm.server || uv tool install -q mlx-lm
mkdir -p "$STATE_HOME/cfg-init-feedback"
cfg launchd org.bearmug.feedback-model "$STATE_HOME/cfg-init-feedback/model.log" \
	"$(command -v mlx_lm.server)" --model mlx-community/Qwen3-1.7B-4bit --host 127.0.0.1 --port 8086 \
	--max-tokens 4 --chat-template-args '{"enable_thinking":false}' \
	--decode-concurrency 1 --prompt-concurrency 1 --prompt-cache-size 2
