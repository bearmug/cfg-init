# cfg-init
Per-machine bootstrap: small, re-runnable recipes for dev tooling.
Debian/Ubuntu-first; macOS notes where the recipe differs.

## Recipes

| Script | Does | Notes |
|---|---|---|
| `cfg-tools-general-purpose.sh` | htop, curl/wget, DB clients, python3-pip, jq, fzf, nvm | nvm pinned (v0.40.7), skipped if `~/.nvm` exists |
| `cfg-tools-git.sh` | git + starter `.gitconfig` / `.gitignore` | `GIT_USER_NAME`/`GIT_USER_EMAIL` env or prompt; `--no-prompt` for CI; backs up existing files |
| `cfg-tools-docker.sh` | Docker CE + Compose plugin via keyring/signed-by | installs `docker compose` plugin (not the old standalone binary); re-logon for the `docker` group |
| `cfg-tools-gradle.sh` | Gradle via SDKMAN + daemon/parallel config | version switches via `sdk`; copies `home/.gradle/gradle.properties` |
| `cfg-tools-tmux.sh` | tmux + `.tmux.conf` + TPM plugin install | installs TPM (previously missing), then plugins |
| `cfg-tools-oh-my-zsh.sh` | zsh + Oh My Zsh + 2 plugins | canonical `ohmyzsh/ohmyzsh` URL, unattended, idempotent plugin list |
| `cfg-tools-omp.sh` | OMP spend tuning + headroom MCP | per-key `omp config set`, merges `mcp.json` |
| `cfg-tools-model-gate.sh` | optional model-agnostic local gate | see below |

Run from the repo root (`./cfg-tools-*.sh` resolve their `home/` payloads
relative to the script). Scripts are `set -euo pipefail` and re-run safe:
existing user files get timestamped backups or merge-updates, never silent
clobbers.

## Conventions

* One script, one concern; `<area>-<tool>.sh` naming (`cfg-tools-*`).
* Shared dotfiles live under `home/` and are copied in by the matching recipe.
* Prefer per-key/appends over whole-file overwrites for user-owned config.
* macOS: `apt` recipes don't apply; use `brew` equivalents by hand
  (the model-gate and OMP recipes are the portable ones).

## Starter configs

* `home/.gitconfig` — log/status/branch aliases (`l`, `s`, `sb`, `b`, `la`…);
  identity is filled from env/prompt at install time.
* `home/.gitignore-file` — home-dir oriented ignore starter.
* `home/.gradle/gradle.properties` — daemon + parallel + configure-on-demand.
* `home/.tmux.conf` — `C-a` prefix, Alt-arrow navigation, TPM + sensible/solarized.
* `home/.omp/agent/` — spend-tuned `config.yml` mirror plus headroom `mcp.json`.

## OMP agent defaults

* Applied with `cfg-tools-omp.sh`; keys mirror `home/.omp/agent/config.yml`.
* Minimum spend: compaction at 280k/200k tokens, usage + cache-miss markers,
  tool-result imaging on.
* Headroom MCP (`uv tool install --python 3.13 "headroom-ai[all]"`, stdio).

## Optional local model gate

* `cfg-tools-model-gate.sh` installs a small Bun proxy at `~/.local/share/model-gate/`.
* Model-agnostic; forwards OpenAI-compatible `/v1` requests to `127.0.0.1:8080` by default.
* `MODEL_GATE_UPSTREAM`, `MODEL_GATE_PORT`, `MODEL_GATE_LIMIT` point it at another backend.
* Immediate HTTP 503 in macOS Low Power Mode or when saturated — no queue —
  so OMP falls over to its configured fallback.
* Bonsai 2 is the tested example/default: subagents route local, GPT-5.6 Luna spills over.
* Start the proxy under a supervisor (e.g. OMP `hub`), not a bare background shell.

## Retired

Removed 2026-09 as stale, broken, or superseded (kept in git history):

* `cfg-stack-jdk.sh` — pinned JDK 8–13 via `openjdk-r` PPA + interactive
  `update-alternatives`; use `sdk install java` / `sdkman` or `apt install temurin-*` instead.
* `cfg-stack-erl.sh` — built OTP 21.3 from source via kerl; use `kerl`/`asdf`/`mise`
  with a current OTP (29.x) if you need Erlang.
* `cfg-tools-gradle.sh` (old PPA path) — retired `cwchien/gradle` PPA
  (last published for Ubuntu mantic); the recipe now uses SDKMAN.
* `cfg-tools-idea.sh` — curled a font script and opened the Toolbox page in a
  browser; install JetBrains Toolbox / fonts directly.
* `cfg-tools-micro.sh` — installed `micro` via snap; `apt install micro`
  or your editor of choice covers it.
* `cfg-tools-visual.sh` — kubuntu-desktop + archived `jonls/redshift`
  + X11-only `xdotool` gestures; use your DE's Night Light and native
  Wayland gestures instead.
* `cfg-fix-display-resolution.sh` — one-off `xrandr Virtual1` 1080p stanza for
  old Ubuntu VMs; use your hypervisor display settings.
