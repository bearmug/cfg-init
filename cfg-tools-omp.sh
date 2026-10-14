#!/bin/bash

# Tune OMP without replacing unrelated user configuration.
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(omp config path)"

# Install the local context-compression tool and TypeScript LSP prerequisites.
uv tool install --python 3.13 "headroom-ai[all]"
bun install -g typescript typescript-language-server@6.0.1
LSP_BIN="$(command -v typescript-language-server)"
HEADROOM_BIN="$(uv tool dir --bin)/headroom"

mkdir -p "$AGENT_DIR"
# Apply home/.omp/agent/config.yml, the single source of these settings.
python3 - "$AGENT_DIR" "$SCRIPT_DIR/home/.omp/agent" "$LSP_BIN" "$HEADROOM_BIN" <<'EOF'
import json, re, subprocess, sys
from pathlib import Path

target_dir, template_dir = map(Path, sys.argv[1:3])
lsp_command = sys.argv[3]

def omp_config(*args):
    return subprocess.run(["omp", "config", *args], check=True, text=True, stdout=subprocess.PIPE).stdout

def read_yaml(path):
    if not path.exists():
        return {}
    parse = "console.log(JSON.stringify(Bun.YAML.parse(await Bun.stdin.text()) ?? {}))"
    return json.loads(subprocess.run(["bun", "-e", parse], input=path.read_text(), check=True,
                                     text=True, stdout=subprocess.PIPE).stdout)

catalog = json.loads(omp_config("list", "--json"))
# Records merge with the global file only: `omp config get` also returns project/overlay layers.
# OMP keeps updating an existing config.yaml when no config.yml exists.
global_file = target_dir / "config.yml"
stored = read_yaml(global_file if global_file.exists() else target_dir / "config.yaml")

def apply_settings(prefix, values):
    for name, value in values.items():
        key = prefix + name
        kind = catalog.get(key, {}).get("type")
        if kind == "record":
            # Merge per entry so unrelated user roles, chains and thresholds survive.
            record = stored
            for part in key.split("."):
                record = record.get(part) if isinstance(record, dict) else None
            value = {**(record or {}), **value}
        elif kind is None and isinstance(value, dict):
            apply_settings(key + ".", value)
            continue
        text = value if isinstance(value, str) else json.dumps(value)
        omp_config("set", key, "--", text)

apply_settings("", read_yaml(template_dir / "config.yml"))

path = target_dir / "APPEND_SYSTEM.md"
section = (template_dir / path.name).read_text()
original = path.read_bytes().decode("utf-8") if path.exists() else ""
match = re.search(r"(?m)^## Delegation policy[ \t]*\r?$", original)
if match:
    next_heading = re.search(r"(?m)^#{1,2}[ \t]+", original[match.end():])
    end = match.end() + next_heading.start() if next_heading else len(original)
    updated = original[:match.start()] + section + original[end:]
else:
    separator = "" if not original or original.endswith("\n\n") else "\n" if original.endswith("\n") else "\n\n"
    updated = original + separator + section
path.write_text(updated)

path = target_dir / "mcp.json"
config = json.loads(path.read_text()) if path.exists() else {}
template = json.loads((template_dir / path.name).read_text())
config.setdefault("mcpServers", {}).update(template["mcpServers"])
# GUI/ACP launches may lack uv's tool bin on PATH; use the installed binary.
config["mcpServers"]["headroom"]["command"] = sys.argv[4]
path.write_text(json.dumps(config, indent=2) + "\n")

path = target_dir / "lsp.json"
config = json.loads(path.read_text()) if path.exists() else {}
template = json.loads((template_dir / path.name).read_text())
server = template["servers"]["typescript-language-server"]
existing = config.setdefault("servers", {}).setdefault("typescript-language-server", server.copy())
existing.update(command=lsp_command, args=server["args"])
path.write_text(json.dumps(config, indent=2) + "\n")
EOF
