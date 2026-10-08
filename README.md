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
| `cfg-tools-omp.sh` | OMP native judge, compaction, LSP + headroom MCP | merge-safe configuration and delegation preprompt |
| `cfg-tools-model-gate.sh` | optional model-agnostic local gate | see below |
| `cfg-tools-telegram-intervention.sh` | portable Telegram intervention skill | explicit harness skill directory; environment-only credentials |

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
* `home/.omp/agent/` — OMP `config.yml`, delegation `APPEND_SYSTEM.md`,
  TypeScript `lsp.json`, and headroom `mcp.json`.

## OMP agent defaults

* located under **home/.omp/agent/** and applied with **cfg-tools-omp.sh**:
  per-key OMP settings plus one Python merge pass preserve unrelated user config.
* configures compaction at 80%, retaining the 200k-token / 180-second idle
  behavior, token usage and cache-miss markers, and snapcompact's auto shape,
  no system prompt, and tool results
* selects the native `typesafe/jev-latest` judge with the paid
  `opencode-zen-jev/jev-1.13` retry fallback; model authentication/provider
  credentials must already be configured. Provisioning does not download
  models. The paid fallback is used to avoid treating uncalibrated Luna
  prompted-judge confidence as authoritative.
* enables task LSP and TypeScript server support (`typescript` and
  `typescript-language-server@6.0.1` installed via Bun); `home/.omp/agent/lsp.json`
  merges the named server into existing per-user server configuration.
* provisions the delegation policy from `home/.omp/agent/APPEND_SYSTEM.md`:
  benefit-based delegation, main-owned orchestration, bounded worker briefs,
  capability/cost-aware selection, independent slices dispatched together,
  and evidence-backed acceptance. Replaces only the `## Delegation policy`
  section; preserves unrelated preprompt instructions and does not duplicate
  the section on re-runs.
* requires `omp`, Bun, and `uv`; the script installs `headroom-ai[all]` with
  Python 3.13 using uv. Add Bun's global binary directory to `PATH` before
  running the script.
* Native OMP experimental context management remains disabled. Global OMP
  notes remain disabled.

## cmux link routing

For external-only links, run `cmux disable-browser` and merge these preferences
into `~/.config/cmux/cmux.json` (back up the existing file; preserve other keys):

```json
{
  "browser": {
    "openTerminalLinksInCmuxBrowser": false,
    "interceptTerminalOpenCommandInCmuxBrowser": false
  }
}
```

Run `cmux reload-config` afterward. External links use the macOS default browser;
select Google Chrome as the default for both HTTP and HTTPS for Chrome-only
routing. On the current workstation, both already use `com.google.chrome`;
an actual `cmux open` link was observed in Chrome with no internal browser surface.

## Optional local model gate

* `cfg-tools-model-gate.sh` installs a small Bun proxy at `~/.local/share/model-gate/`.
* Model-agnostic; forwards OpenAI-compatible `/v1` requests to `127.0.0.1:8080` by default.
* `MODEL_GATE_UPSTREAM`, `MODEL_GATE_PORT`, `MODEL_GATE_LIMIT` point it at another backend.
* Immediate HTTP 503 in macOS Low Power Mode or when saturated — no queue —
  so OMP falls over to its configured fallback.
* Bonsai 2 is the tested example/default: subagents route local, GPT-5.6 Luna spills over.
* Start the proxy under a supervisor (e.g. OMP `hub`), not a bare background shell.

## Telegram intervention skill

`skills/telegram-intervention/` is a harness-agnostic skill for the primary case:
user intervention is required to unblock current agent work. Completion alerts
are optional. Python 3 is the only local runtime dependency.

```sh
./cfg-tools-telegram-intervention.sh /path/to/harness/skills
```

Choose the skill search path supported by your harness; the recipe deliberately
does not assume OMP, Claude Code, Codex, or another harness. Existing skill files
are backed up before replacement. Add the **Harness integration rule** from
`SKILL.md` to persistent agent instructions so blockers trigger skill loading.
For a harness without skill discovery, include `SKILL.md` in its instructions
and give it the absolute path to `scripts/notify.py`.

Configure the sender's environment through your harness secret store or launcher:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | required bot token; never commit or put in prompts |
| `TELEGRAM_CHAT_ID` | required destination user/group ID |
| `TELEGRAM_MESSAGE_THREAD_ID` | optional positive forum topic ID |
| `TELEGRAM_NOTIFY_DONE` | set to `1` for verified completion alerts; off by default |

Create your bot with Telegram's BotFather and start it from the destination user
account (or add it to the group). Obtain the destination ID using Telegram tooling
outside agent prompts; keep token-bearing API URLs out of logs. No credentials
are bundled, generated, or persisted by this recipe or sender.

Smoke the installed sender from the configured execution environment:

```sh
printf '%s\n' 'blocked: setup — confirm receipt in the agent thread.' \
  | python3 /path/to/harness/skills/telegram-intervention/scripts/notify.py blocked
```

The sender uses HTTPS `sendMessage`, plain text, no link previews, and a 15-second
network timeout. It exits nonzero on failure without printing secret-bearing
URLs or response bodies. It does not retry ambiguous delivery failures.
The agent owns per-blocker deduplication and sends completion once after
verification (`done --force` permits an explicit one-off request).

Validate integration by giving the harness a task that requires a user decision:
it should open its native intervention UI, send one Telegram alert identifying
the task/action, and wait without repeated alerts. Respond in the harness and
verify work resumes. Telegram is notification-only: replies do not grant approval
or resume agents. Skill instructions cannot enforce behavior in a harness that
does not load them. No live Telegram delivery is verified by repository-only
checks; deployment requires the separately supplied credentials and receipt check.

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
