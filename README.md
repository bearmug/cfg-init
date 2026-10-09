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
| `cfg-tools-omp.sh` | OMP native judge, compaction, LSP + headroom MCP | merge-safe configuration and delegation preprompt |
| `cfg-tools-feedback.sh` | portable dissatisfaction skill + OMP/T3 adapters | tiny local MLX scorer on macOS; approval-gated worktrees |
| `cfg-tools-telegram-intervention.sh` | portable Telegram intervention skill | explicit harness skill directory; environment-only credentials |
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
* Optional local-AI packages install runtimes only. The feedback scorer's first
  inference separately downloads its configured model weights.

## Starter configs

* `home/.gitconfig` — log/status/branch aliases (`l`, `s`, `sb`, `b`, `la`…);
  identity is filled from env/prompt at install time.
* `home/.config/git/ignore` — conservative global ignore for OS/editor/build
  noise and local environment files; `.env.example` remains trackable.
* `home/.gradle/gradle.properties` — daemon, parallel, and
  configure-on-demand settings.
* `home/.tmux.conf` — `C-a` prefix, Alt-arrow navigation, TPM plus
  sensible/solarized.
* `home/.omp/agent/` — OMP `config.yml`, delegation `APPEND_SYSTEM.md`,
  TypeScript `lsp.json`, and headroom `mcp.json`.
* `home/.omp/agent/config.local.example.yml` and
  `models.local.example.yml` — provider-neutral loopback templates only; they
  are not copied automatically and contain no credentials or private paths.

* The generic gate script deliberately does not edit OMP routing. The separate
  Bonsai example applies model roles, per-agent overrides, and fallback chains
  only when explicitly run.

## OMP agent defaults

* Applied with `cfg-tools-omp.sh`: per-key OMP settings plus one Python merge
  pass preserve unrelated user config.
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

### T3 coordinator-owned OMP workers

`cfg-tools-feedback.sh --skip-model` also installs the T3 routing helper, ACP
worker ingress guard, OMP execution-time extension, and `~/.omp/agent/t3.yml`.
It merge-updates only the delegation preprompt section and backs up changed
payloads. Keep T3's OMP `commandPath` on the installed `omp-feedback` launcher;
new ACP processes pick up these changes. Standalone OMP settings are untouched.

Default child selection is **OMP / Sol 6.1 / thinking auto**. Sequential
bugfixes and consequential uncertainty stay on Sol. Deliberately choose
`economy` for bounded extraction or mechanical work; it selects OMP Luna 6,
not an automatic downgrade. User pins use `pinned` with explicit provider,
model, supported options, and reason. There is no silent model fallback.

From the coordinator, send assignment JSON on stdin:

```sh
python3 ~/.local/share/cfg-init-feedback/t3_policy.py delegate <<'JSON'
{
  "task": "Inspect the specified issue. Include source references, constraints, owned paths, interfaces, deliverable and acceptance checks here.",
  "title": "[sub] [bugs] inspect bounded issue",
  "role": "research",
  "clientRequestId": "bounded-issue-round-1"
}
JSON
```

Add `"lane":"economy","reason":"bounded read-only extraction"` to select Luna.
For a user pin, add `"lane":"pinned"`, a reason, and `"target"` with
`providerInstanceId`, `model`, and an options object. The helper resolves the
live catalog, injects worker constraints, checks the returned model/options,
and cancels unverified launches. Its private
`~/.local/state/cfg-init-t3/delegations.jsonl` journal (or `XDG_STATE_HOME`)
records requested/resolved selection, routing reason and task/thread IDs,
not assignment bodies or host credentials. Retain IDs; consume results through
T3's normal task lifecycle instead of polling.

Workers return questions and missing permissions as **BLOCKED** to the
coordinator. They do not spawn descendants or ask users. The relay rejects
additional child prompts, including after reconnect, and cancels question
elicitations. Answers require a new bounded delegation round, not a continued
child thread. The extension blocks native spawning and child question,
thread-creation and scheduling routes; the helper refuses child delegation.
Feedback screening does not recursively observe child tasks.

**Host limits:** T3 still displays app-owned child composers; cfg-init rejects
input at ACP ingress rather than hiding the UI. Security permission requests
and responses pass unchanged to T3, so required host approval UI is an
intentional exception—not an ordinary worker question or fabricated consent.
Full server-side recursion prevention and relocating security approvals require
T3 changes. These cooperative guards are not a sandbox: unrestricted shell code,
raw authenticated API calls, and explicitly pinned other harnesses can bypass
local OMP hooks. Do not claim application-wide enforcement.


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

Screened, concrete improvements enter `needs_approval` and arrive with an
explanation and **Yes / No** choices in the originating harness. Yes authorizes
only that proposal; No declines it; dismissing the choice leaves it pending.
The main conversation stays on its original topic. Approved work runs in a fresh
agent process and separate Git worktree, returning uncommitted changes and a report
for review. Nothing is installed, merged, pushed, or applied to the original
checkout automatically. This is **not an OS security sandbox**.
Missing details still use `needs_input`. `/feedback` recovers pending choices;
`/feedback resolve EVENT_ID ANSWER` remains available for clarification/review.
Decisions are bound to an event and approval token, so stale or repeated choices
cannot authorize a different proposal or launch duplicate work.
On macOS, pending questions and review-ready work trigger a native notification;
the queue remains authoritative if notifications are hidden by Focus/settings.
`FEEDBACK_NOTIFY_COMMAND` is a JSON argv array receiving one text argument.
Set it to `""` to disable, or `["tg-notify"]` to opt into Telegram alerts.
Notification errors stay visible and never retry completed screening/work.

### T3 / ACP coverage

OMP's `input` extension event covers interactive submissions, not raw ACP
ingress. For T3, set the existing OMP provider's `commandPath` to
`~/.local/bin/omp-feedback` (an absolute expanded path) and keep `commandArgs`
`["acp"]`. New ACP processes use the relay, which observes `session/prompt`
before command routing. T3 caller credentials stay in session memory, never
feedback records. For T3 scalar questions it converts plain `oneOf` choices
to an equivalent `enum`, because current T3 does not render `oneOf` choices.
Other protocol messages retain their original bytes except the worker guards
documented above; security permissions remain unchanged.
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

OMP interactive mode uses its native selector. In T3, screened proposals return
to the coordinator through caller-bound `t3_thread_send`; the coordinator asks
the explained Yes/No question in the main conversation and records only an
explicit decision. No choice-only child is created. Child prompts are not
scored. The adapters obtain their own screened result in a background
subprocess—no polling, socket broker, or presentation daemon.
Other ACP harnesses can configure `FEEDBACK_PRESENT_COMMAND`, a JSON argv presenter
receiving the public proposal on stdin. Unsupported hosts retain pending proposals
in `/feedback` rather than pretending to display a card.
`FEEDBACK_IMPLEMENT_COMMAND` can select a different independent implementation
agent. See the skill for its stdin/stdout and worktree contract.

Configuration is merge-installed at `~/.config/cfg-init-feedback/config.json`.
`FEEDBACK_DISABLED=1` disables observation; `FEEDBACK_MODEL_URL` and
`FEEDBACK_MODEL` select the local backend. Screening subprocesses disable
extensions, skills, rules, session persistence, and ambient system-prompt
files to prevent recursion and unrelated repository assumptions.
Screening is deliberately tool-free Luna work. Approved implementation defaults
to Sol 6.1 with auto thinking (`FEEDBACK_IMPLEMENT_MODEL` can explicitly pin it);
it no longer inherits the screening model. Both phases disable model fallback
and strip inherited caller-bound T3 credentials from the standalone process.
See the skill for queue protocol, retention, threshold, timeouts and retry
controls. Inspect status from any harness:

```sh
python3 ~/.agents/skills/dissatisfaction/feedback.py status
```

Stop the macOS scorer with
`launchctl bootout gui/$(id -u)/org.bearmug.feedback-model`; reinstalling starts
it again. Removing the extension and restoring T3's original OMP command
disables ingress observation without deleting queued evidence.

CI runs the deterministic feedback queue, approval safety, ACP, and isolated
implementation regressions:
`python3 -m unittest discover -s home/.agents/skills/dissatisfaction -v`.

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
