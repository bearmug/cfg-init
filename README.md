# cfg-init
Per-machine bootstrap: small, re-runnable recipes for developer tooling.
Debian/Ubuntu-first, with an explicit macOS Homebrew path.

## Recipes

| Script or file | Does | Notes |
|---|---|---|
| `cfg-tools-general-purpose.sh` | htop, curl/wget, DB clients, python3-pip, jq, fzf, nvm | Linux baseline; nvm is pinned to v0.40.7 and skipped if `~/.nvm` exists |
| `cfg-tools-git.sh` | git plus starter `.gitconfig` and global ignore | `GIT_USER_NAME`/`GIT_USER_EMAIL` env or prompt; `--no-prompt` for CI; backs up existing files; never enables plaintext credential storage |
| `cfg-tools-docker.sh` | Docker CE plus Compose plugin via keyring/signed-by | Supports Debian and Ubuntu; installs `docker compose`, not the old standalone binary |
| `cfg-tools-gradle.sh` | Gradle through SDKMAN plus daemon/parallel config | Installs only when SDKMAN has no current Gradle; version switches stay with `sdk` |
| `cfg-tools-tmux.sh` | tmux, `.tmux.conf`, and TPM plugin install | Installs TPM when missing, then plugins |
| `cfg-tools-oh-my-zsh.sh` | zsh, Oh My Zsh, and two plugins | Canonical `ohmyzsh/ohmyzsh` URL; unattended and idempotent |
| `cfg-tools-omp.sh` | OMP spend tuning plus headroom MCP | Per-key `omp config set`; merges `mcp.json` |
| `cfg-tools-model-gate.sh` | Optional model-agnostic local Bun gate | Installs the proxy only; provider/model routing is separate |
| `cfg-tools-model-gate-bonsai.sh` | Explicit Bonsai OMP routing example | Opt-in example; requires `omp` and `python3`; all values are overrideable |
| `Brewfile` / `cfg-tools-macos.sh` | macOS Homebrew baseline | Requires Homebrew; `CFG_INIT_LOCAL_AI=1` adds optional Ollama and llama.cpp packages |
| `cfg-doctor.sh` | Read-only workstation/config checks | Warnings are non-fatal; `CFG_INIT_CHECK_LOCAL_AI=1` also probes optional local endpoints |

Run from the repository root so each recipe can resolve its `home/` payloads:

```sh
./cfg-doctor.sh
./cfg-tools-macos.sh                 # macOS + Homebrew
CFG_INIT_LOCAL_AI=1 ./cfg-tools-macos.sh
```

Most installation recipes use strict shell modes and are intended to be
re-runnable. Existing user files are backed up or merge-updated by the matching
recipe; the doctor performs no writes.

## Conventions

* One script, one concern; `<area>-<tool>.sh` naming (`cfg-tools-*`).
* Shared dotfiles live under `home/` and are copied by the matching recipe.
* Prefer per-key/appends over whole-file overwrites for user-owned config.
* Linux package recipes target Debian or Ubuntu. macOS uses `Brewfile`; it does
  not run `apt` recipes.
* Optional local-AI packages install runtimes only. cfg-init never downloads
  model weights.

## Starter configs

* `home/.gitconfig` — log/status/branch aliases (`l`, `s`, `sb`, `b`, `la`…);
  identity is filled from env/prompt at install time.
* `home/.config/git/ignore` — conservative global ignore for OS/editor/build
  noise and local environment files; `.env.example` remains trackable.
* `home/.gradle/gradle.properties` — daemon, parallel, and
  configure-on-demand settings.
* `home/.tmux.conf` — `C-a` prefix, Alt-arrow navigation, TPM plus
  sensible/solarized.
* `home/.omp/agent/` — spend-tuned `config.yml` mirror plus headroom `mcp.json`.
* `home/.omp/agent/config.local.example.yml` and
  `models.local.example.yml` — provider-neutral loopback templates only; they
  are not copied automatically and contain no credentials or private paths.

## OMP agent defaults

* Applied with `cfg-tools-omp.sh`; keys mirror `home/.omp/agent/config.yml`.
* Minimum spend: compaction at 280k/200k tokens, usage and cache-miss markers,
  and tool-result imaging enabled.
* Headroom MCP uses
  `uv tool install --python 3.13 "headroom-ai[all]"` and stdio.
* The generic gate script deliberately does not edit OMP routing. The separate
  Bonsai example applies model roles, per-agent overrides, and fallback chains
  only when explicitly run.

## Optional local model gate

* `cfg-tools-model-gate.sh` installs a small Bun proxy at
  `~/.local/share/model-gate/`.
* It is model-agnostic and forwards OpenAI-compatible `/v1` requests to
  `127.0.0.1:8080` by default. `MODEL_GATE_UPSTREAM`, `MODEL_GATE_PORT`, and
  `MODEL_GATE_LIMIT` select another backend, port, or concurrency limit.
* Low Power Mode or saturation returns HTTP 503 immediately, without a queue,
  so OMP can use its configured fallback.
* `cfg-tools-model-gate-bonsai.sh` is an explicit routing example, not a
  hidden default. Set `CFG_INIT_BONSAI_MODEL`, `CFG_INIT_BONSAI_PROVIDER`, or
  `CFG_INIT_OMP_FALLBACK` to adapt it to a local setup.
* Start the proxy under a supervisor (for example, OMP `hub`), not a bare
  background shell.

## Security and privacy boundary

* No committed credentials, API keys, access tokens, model weights, private
  workstation paths, or active local configuration are part of the recipes.
* Local OMP examples use loopback endpoints and placeholder model IDs. Replace
  them locally; do not copy a workstation's active `~/.omp/agent/config.yml` or
  `models.yml` into this repository.
* The Git recipe avoids `credential.helper store`; when an OS credential helper
  is available it uses that helper, otherwise Git prompts normally.
* CI checks shell syntax, the model-gate JavaScript, patch whitespace, and common
  private-key/token signatures in tracked files.

## Retired

Removed 2026-09 as stale, broken, or superseded (kept in git history):

* `cfg-stack-jdk.sh` — pinned JDK 8–13 via `openjdk-r` PPA plus interactive
  `update-alternatives`; use `sdk install java` / SDKMAN or `apt install temurin-*` instead.
* `cfg-stack-erl.sh` — built OTP 21.3 from source via kerl; use `kerl`/`asdf`/`mise`
  with a current OTP (29.x) if you need Erlang.
* `cfg-tools-gradle.sh` (old PPA path) — retired `cwchien/gradle` PPA;
  the recipe now uses SDKMAN.
* `cfg-tools-idea.sh` — curled a font script and opened the Toolbox page in a
  browser; install JetBrains Toolbox or fonts directly.
* `cfg-tools-micro.sh` — installed `micro` via snap; `apt install micro` or
  your editor of choice covers it.
* `cfg-tools-visual.sh` — kubuntu-desktop plus archived `jonls/redshift` and
  X11-only `xdotool` gestures; use your DE's Night Light and native Wayland
  gestures instead.
* `cfg-fix-display-resolution.sh` — one-off `xrandr Virtual1` 1080p stanza for
  old Ubuntu VMs; use your hypervisor display settings.
