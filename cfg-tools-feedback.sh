#!/bin/bash
# Portable skill + OMP adapters; macOS optionally supervises the small Metal scorer.
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null
command -v omp >/dev/null
export FEEDBACK_PYTHON="$(command -v python3)"
export FEEDBACK_OMP_BIN="$(command -v omp)"
export FEEDBACK_SOURCE="$ROOT_DIR"
python3 - <<'PY'
import json, os, shutil, sys
from pathlib import Path
root, home = Path(os.environ['FEEDBACK_SOURCE']), Path.home()
for relative in ('.agents/skills/dissatisfaction', '.local/share/cfg-init-feedback'):
    source, target = root / 'home' / relative, home / relative
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file() and not path.name.startswith('test_'):
            destination = target / path.name
            if destination.exists() and destination.read_bytes() != path.read_bytes():
                from datetime import datetime
                shutil.copy2(destination, str(destination) + '.bak-' + datetime.now().strftime('%Y%m%d%H%M%S'))
            shutil.copy2(path, destination)
skills = home / '.omp/agent/skills/dissatisfaction'
skills.mkdir(parents=True, exist_ok=True)
source, target = root / 'home/.agents/skills/dissatisfaction/SKILL.md', skills / 'SKILL.md'
if target.exists() and target.read_bytes() != source.read_bytes():
    from datetime import datetime
    shutil.copy2(target, str(target) + '.bak-' + datetime.now().strftime('%Y%m%d%H%M%S'))
shutil.copy2(source, target)
extensions = home / '.omp/agent/extensions'
extensions.mkdir(parents=True, exist_ok=True)
source = root / 'home/.omp/agent/extensions/dissatisfaction.ts'
target = extensions / source.name
if target.exists() and target.read_bytes() != source.read_bytes():
    from datetime import datetime
    shutil.copy2(target, str(target) + '.bak-' + datetime.now().strftime('%Y%m%d%H%M%S'))
shutil.copy2(source, target)
config_path = home / '.config/cfg-init-feedback/config.json'
config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
config = json.loads(config_path.read_text()) if config_path.exists() else {}
defaults = {
    'FEEDBACK_PYTHON': os.environ['FEEDBACK_PYTHON'],
    'FEEDBACK_OMP_BIN': os.environ['FEEDBACK_OMP_BIN'],
    'FEEDBACK_MODEL_URL': 'http://127.0.0.1:8086/v1',
    'FEEDBACK_MODEL': 'mlx-community/Qwen3-1.7B-4bit',
    'FEEDBACK_SCREEN_COMMAND': json.dumps([os.environ['FEEDBACK_PYTHON'], str(home / '.local/share/cfg-init-feedback/screen_omp.py')]),
    'FEEDBACK_SCREEN_MODEL': 'openai-codex/gpt-6-luna',
    'FEEDBACK_SCREEN_TIMEOUT': '660',
}
if sys.platform == 'darwin':
    defaults['FEEDBACK_NOTIFY_COMMAND'] = json.dumps([
        '/usr/bin/osascript', '-e',
        'on run argv\n display notification (item 1 of argv) with title "Assistant feedback"\nend run'
    ])
for key, value in defaults.items():
    config.setdefault(key, value)
config_path.write_text(json.dumps(config, indent=2) + '\n')
config_path.chmod(0o600)
bin_dir = home / '.local/bin'
bin_dir.mkdir(parents=True, exist_ok=True)
launcher = bin_dir / 'omp-feedback'
import shlex
launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(os.environ['FEEDBACK_PYTHON']) + ' ' +
                    shlex.quote(str(home / '.local/share/cfg-init-feedback/omp_acp.py')) + ' "$@"\n')
launcher.chmod(0o755)
print('Skill installed; T3 OMP commandPath: ' + str(launcher))
print('Feedback configuration: ' + str(config_path))
PY
if [[ "${1:-}" == "--skip-model" ]]; then
    echo "Model service skipped; configure a loopback OpenAI-compatible scorer."
    exit 0
fi
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "MLX service requires macOS; configure FEEDBACK_MODEL_URL for your local backend."
    exit 0
fi
command -v mlx_lm.server >/dev/null || uv tool install mlx-lm
export FEEDBACK_MLX_SERVER="$(command -v mlx_lm.server)"
python3 - <<'PY'
import os, plistlib, subprocess
from pathlib import Path
home = Path.home()
label = 'org.bearmug.feedback-model'
path = home / 'Library/LaunchAgents' / (label + '.plist')
path.parent.mkdir(parents=True, exist_ok=True)
state = home / '.local/state/cfg-init-feedback'
state.mkdir(parents=True, exist_ok=True, mode=0o700)
record = {'Label': label, 'ProgramArguments': [os.environ['FEEDBACK_MLX_SERVER'], '--model',
          'mlx-community/Qwen3-1.7B-4bit', '--host', '127.0.0.1', '--port', '8086',
          '--max-tokens', '4', '--chat-template-args', '{"enable_thinking":false}',
          '--decode-concurrency', '1', '--prompt-concurrency', '1',
          '--prompt-cache-size', '2'], 'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 30,
          'StandardOutPath': str(state / 'model.log'), 'StandardErrorPath': str(state / 'model.log')}
encoded = plistlib.dumps(record)
if path.exists() and path.read_bytes() != encoded:
    raise SystemExit('Existing model LaunchAgent differs; stop it and reconcile manually: ' + str(path))
path.write_bytes(encoded)
subprocess.run(['plutil', '-lint', str(path)], check=True)
service = f'gui/{os.getuid()}/{label}'
if subprocess.run(['launchctl', 'print', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
    subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(path)], check=True)
print('Supervised local model: ' + service)
PY
