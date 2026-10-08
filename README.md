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
| `cfg-tools-feedback.sh` | portable dissatisfaction skill + OMP/T3 adapters | tiny local MLX scorer on macOS; approval-gated worktrees |

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


## Actionable dissatisfaction

Run `./cfg-tools-feedback.sh` to install the harness-independent skill under
`~/.agents/skills/dissatisfaction`, OMP discovery under `~/.omp/agent/skills`,
and the OMP extension. On macOS it also installs a launchd-supervised,
loopback-only MLX server (`org.bearmug.feedback-model`, port 8086).
Use `--skip-model` with an existing local OpenAI-compatible backend.
The first inference downloads model weights; inference does not send prompts
to a remote scoring service.

The scorer is **Qwen3-1.7B, 4-bit, thinking disabled**, not Jev. One-token
YES/NO decoding is constrained with equal logit bias; the two token
log-likelihoods are normalized into a 0–1 score. This is **not an empirically
calibrated probability**. It avoids unreliable generated numeric JSON and
limits decoding work. Few-shot examples cover assistant criticism, praise,
neutral requests and external complaints. Terse reactions can still be missed,
and instruction-like text can score falsely high; screening is a second gate.
The Chrome slop-highlighter uses a Jev-distilled ModernBERT 149M head via
WebGPU; its slop/AI-authorship axis is not a dissatisfaction score.
The 0.5B candidate failed direct-criticism probes and was rejected.
No energy-consumption claim is made: small weights and serialized inference
limit resources, but watts have not been measured.

Every ingress adapter sends the same JSON event to `feedback.py submit`.
It persists an event and starts a detached, single-consumer worker; model
inference and screening never wait on the main agent turn. Failures remain
visible in `status`. A score at least 0.8 (configurable) triggers a
tool-free OMP screening agent to decide actual actionability, using the configured
`openai-codex/gpt-6-luna` model. **High-scoring prompts/context
are sent to that model's provider**; low-scoring prompts stay local.
Override the screening command/model if remote screening is unwanted.
Screening uses an isolated per-run fallback override: the selected model
either succeeds or fails visibly; it is never silently replaced. The Muse
Spark candidate returned 403 during the live smoke and was rejected.
The local backend must support `logit_bias`, `logprobs` and `top_logprobs`.
For a different model, set `FEEDBACK_LABEL_TOKENS` to its single-token YES/NO
IDs; the default Qwen3 tokenizer was verified as YES=14004 and NO=8996.
Missing/invalid likelihoods fail visibly, with no fabricated fallback.

Questions stay in the queue; `/feedback` shows them without starting a model
turn. `/feedback resolve EVENT_ID ANSWER` resumes screening. Only the exact
answer `approve` authorizes implementation, in a new Git worktree; nothing
is merged, pushed, or applied to the active checkout automatically. This is
process/workspace separation, **not an OS security sandbox**. Approval runs
a tool-enabled agent; review its work before merging. Unsaved changes in the
original checkout are not copied into the worktree.
On macOS, pending questions and review-ready work trigger a native notification;
the queue remains authoritative if notifications are hidden by Focus/settings.
`FEEDBACK_NOTIFY_COMMAND` is a JSON argv array receiving one text argument.
Set it to `""` to disable, or `["tg-notify"]` to opt into Telegram alerts.
Notification errors stay visible and never retry completed screening/work.

### T3 / ACP coverage

OMP's `input` extension event covers interactive submissions, not raw ACP
ingress. For T3, set the existing OMP provider's `commandPath` to
`~/.local/bin/omp-feedback` (an absolute expanded path) and keep `commandArgs`
as `["acp"]`. New ACP processes use the transparent relay, which observes
`session/prompt` before command routing and preserves normal protocol bytes.
The relay handles `/feedback` locally and emits an ACP assistant-message update,
because OMP custom command messages are not forwarded visibly by ACP.
Existing sessions must reconnect before they can use a newly installed relay.
The wrapper records text prompts plus bounded prior assistant text; images
are not interpreted. Its queue-overflow warning explicitly identifies an
unscored prompt rather than pretending full coverage.
T3's injected instruction envelope is removed before scoring the user request.
Long text is bounded to its first 2,000 and last 6,000 characters, with an
explicit stderr notice. This is text-only bounded coverage, not full-image or
unlimited-transcript understanding.

Configuration is merge-installed at `~/.config/cfg-init-feedback/config.json`.
`FEEDBACK_DISABLED=1` disables observation; `FEEDBACK_MODEL_URL` and
`FEEDBACK_MODEL` select the local backend. Screening subprocesses disable
extensions, skills, rules, session persistence, and ambient system-prompt
files to prevent recursion and unrelated repository assumptions.
See the skill for queue protocol, retention, threshold, timeouts and retry
controls. Inspect status from any harness:

```sh
python3 ~/.agents/skills/dissatisfaction/feedback.py status
```

Stop the macOS scorer with
`launchctl bootout gui/$(id -u)/org.bearmug.feedback-model`; reinstalling starts
it again. Removing the extension and restoring T3's original OMP command
disables ingress observation without deleting queued evidence.

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
