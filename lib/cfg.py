#!/usr/bin/env python3
"""File and config helpers shared by components. Stdlib only.

Every write backs up a differing destination as `<path>.bak-<timestamp>`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

STAMP = datetime.now().strftime("%Y%m%d%H%M%S")


def backup(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, f"{path}.bak-{STAMP}")


def write(path: Path, data: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        status = "unchanged"
    else:
        backup(path)
        path.write_bytes(data)
        status = "installed"
    if mode is not None:
        path.chmod(mode)
    print(f"  {status}: {path}")


def put(src: str, dst: str, mode: str | None = None) -> None:
    """Copy one file."""
    write(Path(dst), Path(src).read_bytes(), int(mode, 8) if mode else None)


def section(dst: str, src: str) -> None:
    """Replace or append the `## Heading` section from src, keeping the rest of dst."""
    path, text = Path(dst), Path(src).read_text()
    heading = text.splitlines()[0].strip()
    original = path.read_text() if path.exists() else ""
    match = re.search(rf"(?m)^{re.escape(heading)}[ \t]*\r?$", original)
    if match:
        rest = re.search(r"(?m)^#{1,2}[ \t]+", original[match.end():])
        end = match.end() + rest.start() if rest else len(original)
        updated = original[:match.start()] + text + original[end:]
    else:
        updated = original.rstrip() + ("\n\n" if original else "") + text
    write(path, updated.encode())


def defaults(dst: str, *pairs: str) -> None:
    """Add missing KEY=VALUE string entries to a private JSON file; existing values win."""
    path = Path(dst)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = json.loads(path.read_text()) if path.exists() else {}
    for key, _, value in (pair.partition("=") for pair in pairs):
        config.setdefault(key, value)
    write(path, (json.dumps(config, indent=2) + "\n").encode(), 0o600)


def zshrc(dst: str, theme: str, *plugins: str) -> None:
    """Ensure plugins are listed; replace only the stock robbyrussell theme."""
    path = Path(dst)
    text = path.read_text() if path.exists() else ""
    text = re.sub(r'(?m)^ZSH_THEME="robbyrussell".*$', f'ZSH_THEME="{theme}"', text)
    match = re.search(r"(?m)^plugins=\(([^)]*)\)", text)
    if match:
        have = match.group(1).split()
        have += [p for p in plugins if p not in have]
        text = text[:match.start(1)] + " ".join(have) + text[match.end(1):]
    else:
        text += f"\nplugins=(git {' '.join(plugins)})\n"
    write(path, text.encode())


def _omp(*args: str) -> str:
    return subprocess.run(["omp", "config", *args], check=True, text=True, stdout=subprocess.PIPE).stdout


def _yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    parse = "console.log(JSON.stringify(Bun.YAML.parse(await Bun.stdin.text()) ?? {}))"
    out = subprocess.run(["bun", "-e", parse], input=path.read_text(), check=True, text=True, stdout=subprocess.PIPE)
    return json.loads(out.stdout)


def omp_settings(template: str, agent_dir: str) -> None:
    """Apply every key of a config.yml template through `omp config set`.

    Record settings merge per entry with the *global* file only (`omp config get`
    also returns project layers), so unrelated user roles/chains survive.
    """
    catalog = json.loads(_omp("list", "--json"))
    agent = Path(agent_dir)
    stored = _yaml(agent / "config.yml" if (agent / "config.yml").exists() else agent / "config.yaml")

    def apply(prefix: str, values: dict) -> None:
        for name, value in values.items():
            key = prefix + name
            kind = catalog.get(key, {}).get("type")
            if kind == "record":
                current = stored
                for part in key.split("."):
                    current = current.get(part) if isinstance(current, dict) else None
                value = {**(current or {}), **value}
            elif kind is None and isinstance(value, dict):
                apply(key + ".", value)
                continue
            _omp("set", key, "--", value if isinstance(value, str) else json.dumps(value))
            print(f"  set: {key}")

    apply("", _yaml(Path(template)))


def lsp_server(template: str, dst: str, name: str, command: str) -> None:
    """Merge one named LSP server into lsp.json, pinning its absolute command."""
    path = Path(dst)
    config = json.loads(path.read_text()) if path.exists() else {}
    server = json.loads(Path(template).read_text())["servers"][name]
    entry = config.setdefault("servers", {}).setdefault(name, dict(server))
    entry.update(command=command, args=server["args"])
    write(path, (json.dumps(config, indent=2) + "\n").encode())


def launchd(label: str, log: str, *argv: str) -> None:
    """Install a KeepAlive user LaunchAgent; a changed definition is reloaded."""
    import plistlib
    path = Path.home() / "Library/LaunchAgents" / f"{label}.plist"
    record = {"Label": label, "ProgramArguments": list(argv), "RunAtLoad": True, "KeepAlive": True,
              "ThrottleInterval": 30, "StandardOutPath": log, "StandardErrorPath": log}
    encoded = plistlib.dumps(record)
    domain = f"gui/{os.getuid()}"
    if path.exists() and path.read_bytes() != encoded:
        subprocess.run(["launchctl", "bootout", f"{domain}/{label}"], stderr=subprocess.DEVNULL)
    write(path, encoded)
    if subprocess.run(["launchctl", "print", f"{domain}/{label}"], capture_output=True).returncode:
        subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    print(f"  running: {domain}/{label}")


if __name__ == "__main__":
    commands = {"put": put, "section": section, "defaults": defaults, "zshrc": zshrc,
                "omp-settings": omp_settings, "lsp-server": lsp_server, "launchd": launchd}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit("usage: cfg.py " + "|".join(commands) + " ARGS")
    commands[sys.argv[1]](*sys.argv[2:])
