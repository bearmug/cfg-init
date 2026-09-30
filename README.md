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
| `cfg-tools-omp.sh` | OMP native judge, compaction, LSP + headroom MCP | merge-safe configuration; explicit shadow experiments |
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
* `home/.omp/agent/` — OMP `config.yml`, TypeScript `lsp.json`, and headroom `mcp.json`.

## OMP agent defaults

* located under **home/.omp/agent/** and applied with **cfg-tools-omp.sh**
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
* requires `omp`, Bun, and `uv`; the script installs `headroom-ai[all]` with
  Python 3.13 using uv. Add Bun's global binary directory to `PATH` before
  running the script.
* Native OMP experimental context management remains disabled. Global OMP
  notes remain disabled.

### Isolated OMP experiments

`experiments/omp/` contains synthetic fixtures, explicit OMP extensions, local
System One runners, and retained results. Nothing here is automatically loaded
or changes production model roles. No credentials or private session journals
are included. Run from that directory with an authenticated OMP installation:

```sh
OMP_EVAL_CONCURRENCY=1 omp --no-session --no-extensions -e ./evaluate.ts -p /decision-eval
omp --no-session --no-extensions -e ./failover.ts -p /judge-failover
bun score.ts fixtures.jsonl results/hosted-sequential.jsonl results/local-sequential.jsonl results/q4-sequential.jsonl
```

The 58 held-out synthetic states contain 98 routing, relevance, evidence-support,
and action-selection questions. Expected labels are explicit rubrics, not a
production accuracy estimate. Sequential results: Jev 87/98, Luna 90/98,
Decider 2B Q4 79/98, Decider 0.8B 78/98, Laya multilingual 52/98. Hosted
median latencies were 264 ms (Jev) and 1990 ms (Luna); reported total costs
were $0.00143 and $0.00336. A second hosted run varied, so this small sample
does not establish quality superiority. Luna's prompted confidence is not
calibrated native probability. Local replay files used concurrent services
and are not valid isolated latency comparisons. Cold start and energy were
not measured.
Reversing criterion order on all 16 routing fixtures preserved 16/16 for
Jev, Luna, and Q4; Laya scored 14/16. Raw probes and their summary are retained.

`results/local-models.json` records pinned model/package identities. Install
local dependencies and download those public revisions into an isolated
environment; provisioning deliberately does neither. The official Decider HTTP
server does not serve GGUF: `serve-decider-q4.py` wraps the official
`Decider.system_one` SDK with a loopback-only experimental endpoint. Laya
requests must explicitly select `multilingual` and set `max_len=8192`; omitted
selection can route to another checkpoint. `http-evaluate.py --help` describes
response-identity checks. Both services were exercised through `/v1/systemone`
and OMP's native TypeSafe client. Decider can silently truncate; the current
OMP client also discards Laya's routing/truncation metadata. Neither local
model is selected globally.

Fault injection verified paid-chain traversal for HTTP 401/403/429/503.
Timeout exhaustion and caller cancellation did not traverse the fallback;
the fallback is not a guarantee for every failure class.

`results/context.json` records actual session compactions and restart recovery.
The bounded notes trial retained its exact fixture across three real rollovers
and restart, but repeated a single rollover request three times: rejected by
the no-repeat gate. A low-threshold stress trial produced 49 rollovers and
maintenance-loop warnings. Ordinary compaction was exercised twice through
`context-compact.ts` (explicit `/ordinary-context-compact`, isolated `/tmp`
profile only): original requirements and evidence paths survived restart,
while other fixture fields were paraphrased/merged. Print-mode `/compact`
text is not evidence of an actual compaction. Trials were not token-matched;
no cost-efficiency conclusion is claimed. Experimental notes remain disabled.

### Temporary live Decider 0.8B shadow

`shadow-proxy.py` always calls native remote Jev after a best-effort local
Decider 0.8B judgment. Only Jev's original response is returned; there is no
confidence-based acceptance yet. Local timeout (1 second), unavailable service,
or invalid model identity cannot substitute a local answer. The remote timeout
is 8 seconds; remote HTTP status and `Retry-After` propagate to the existing
paid Jev fallback/retry policy. The proxy binds to loopback, uses the caller's
existing Jev credential only for remote requests, and also proxies authenticated
model discovery.

The local contribution files capture the active setup without credentials:
`shadow-models.yml` is the provider-only overlay; `shadow-trial.json` is the
current trial snapshot, including its fixed **2026-10-07 12:04:42 UTC** deadline
(not a new seven-day period on every launch). Merge the overlay into existing
`~/.omp/agent/models.yml` rather than replacing that file. Copy the trial snapshot
only when intentionally reproducing this trial; do not overwrite a newer active
trial or silently renew its deadline.

Install `shadow-requirements.txt` into an isolated persistent environment.
`launch-decider-shadow.sh` expects the pinned public model from
`results/local-models.json` under `~/.omp/agent/cache/decider-shadow/hf`;
the launch scripts perform no downloads. `launch-jev-shadow.sh` reads the fixed
deadline from `~/.omp/agent/telemetry/decider-jev/trial.json`. After that deadline,
the proxy bypasses local inference and continues remote-only; supervised
processes remain installed until explicitly stopped.

`launchagents/` contains portable templates matching the active supervisors.
Render them for this checkout and home directory without installing, activating,
downloading, or calling an inference API:

```sh
python3 experiments/omp/render-shadow-launchagents.py --output-dir /tmp/omp-shadow-launchagents
```

Review the rendered files before copying to `~/Library/LaunchAgents/`. The
renderer changes no OMP settings or active service. Model caches, runtime
environments, Python bytecode, and local telemetry are excluded from repository
contributions; only public synthetic evaluation results are retained here.

The current workstation trial runs for seven days from activation, supervised
by user LaunchAgents `ai.omp.decider-shadow` and `ai.omp.jev-shadow`. Its only
production model change is `providers.typesafe.baseUrl: http://127.0.0.1:18744`
in `~/.omp/agent/models.yml`; judge roles and paid fallback are unchanged.
New OMP processes pick it up; existing model registries require a restart.
This route is deliberately **not** installed by `cfg-tools-omp.sh`.

Local statistics: `~/.omp/agent/telemetry/decider-jev/requests.jsonl`, directory
0700/file 0600. Records contain model identities, timings, failure categories,
numeric token usage, question ordinal/type, probabilities, agreement, and score
deltas—not prompts, question keys, labels, answer strings, or credentials.
Local responses can silently truncate; probability agreement is not proof of
correctness. Report with:

```sh
python3 experiments/omp/shadow-stats.py
```

The report includes local/remote latency percentiles, failures, Jev agreement,
score differences, and hypothetical confidence-gate coverage. Agreement is
not ground-truth accuracy. Missing provider cost is reported as unknown,
not zero; no confidence gate is enabled by this report.

To end the trial, remove only the temporary `providers.typesafe` block from
`~/.omp/agent/models.yml` and restart OMP **before** stopping the services:

```sh
launchctl bootout "gui/$(id -u)/ai.omp.jev-shadow"
launchctl bootout "gui/$(id -u)/ai.omp.decider-shadow"
```

Remove the two corresponding plist files from `~/Library/LaunchAgents/` to
prevent reactivation on login. Existing statistics remain local for analysis.

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
