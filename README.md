# cfg-init

One idempotent installer for my macOS and Debian/Ubuntu workstations: shell, git, tmux,
and an OMP/T3 agent setup with a dissatisfaction feedback loop.

```sh
git clone https://github.com/bearmug/cfg-init && cd cfg-init
./install.sh              # pick components interactively
./install.sh --yes        # defaults, no prompts (agents/CI)
./install.sh --yes omp t3 # selected components
./install.sh check        # read-only health + drift report
```

Agents: see [AGENTS.md](AGENTS.md).

## Components

Run `./install.sh list` for the live list. `*` = default.

| Component | Installs |
|---|---|
| `packages`* | Brewfile (macOS) or apt + uv/bun/omp installers (Linux) |
| `git`* | aliases + global ignore via `include.path`; identity from env or prompt; OS credential helper (moves plaintext `store` entries into it) |
| `zsh`* | Oh My Zsh (default theme), autosuggestions, syntax-highlighting; zsh login shell |
| `tmux`* | `.tmux.conf` (`C-a` prefix, Alt-arrows), TPM plugins |
| `omp`* | native Jev judge, compaction, TS LSP, tier agents, delegation policy |
| `feedback`* | dissatisfaction skill, OMP extension, screening, local MLX scorer (macOS launchd) |
| `t3`* | `omp-feedback` ACP relay, T3 delegation helper, worker guards (needs `feedback`) |
| `notify`* | `tg-notify` Telegram sender |
| `gate` | Bun proxy that 503s local model calls on Low Power Mode/saturation |

## Rules

- Re-runnable. A file that differs from the repo is backed up as `*.bak-<timestamp>` first.
- User config is merged, never replaced: git uses an include, OMP keys go through `omp config set`
  (record keys merge per entry), and only the `## Delegation policy` section of `APPEND_SYSTEM.md`
  is replaced.
- No secrets in the repo. Credentials come from env at install time (`TG_BOT_TOKEN`, `TG_CHAT_ID`)
  or the tools' own login flows (`omp`, `gh auth login`).

## Agent setup

**OMP.** The `judge` role is native `typesafe/jev-latest`, which enables `find`, judged TTSR rules,
`auto` thinking, and smart charts. Its fallbacks stay on Jev. Claude 5 1M-window models compact
at 300k tokens. `agents/{easy,mid,high}-*.md` are the delegation tiers referenced by the policy.

**T3.** In T3, set the OMP provider's `commandPath` to `~/.local/bin/omp-feedback` with args
`["acp"]`. The relay feeds every prompt to the feedback loop and enforces worker rules on
delegated children. Coordinators delegate through
`~/.local/share/cfg-init-feedback/t3_policy.py delegate` (JSON assignment on stdin). It defaults
to Sol 6.1, uses Luna for `"lane":"economy"`, and requires an explicit pin for anything else.
Children return `BLOCKED` instead of asking the user. These guards are cooperative, not a sandbox.

**Feedback.** Every prompt is scored locally (Qwen3-1.7B on `127.0.0.1:8086`). Prompts above the
threshold go to a tool-free OMP screening agent, so those prompts reach that model's provider.
Concrete improvements come back as Yes/No proposals. Approved work runs in a separate git worktree
and is never merged automatically. Run `/feedback` to see pending items. Configuration lives in
`~/.config/cfg-init-feedback/config.json`; the skill's details are in
[SKILL.md](home/.agents/skills/dissatisfaction/SKILL.md).

## Layout

```
install.sh        entrypoint          lib/cfg.sh, lib/cfg.py   shared helpers
components/*.sh   one per component   lib/check.sh             `install.sh check`
home/             payloads, mirrored to $HOME
```
