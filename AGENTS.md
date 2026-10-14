# Agent guide

## Setting up a machine

1. `./install.sh check` shows the current state. It is read-only. Lines start with `ok`, `warn`,
   or `FAIL`, and the exit code is 1 when any line is `FAIL`.
2. Install non-interactively: `./install.sh --yes [component..]`. With no components it installs
   the defaults. `./install.sh list` shows what is available.
   - `git` needs `GIT_USER_NAME` and `GIT_USER_EMAIL` when no identity is configured yet.
   - `notify` writes credentials only from `TG_BOT_TOKEN` and `TG_CHAT_ID`. Never invent them.
   - `FEEDBACK_SKIP_MODEL=1` skips the local scorer service, for example when the backend is
     remote or the machine runs Linux.
3. Run `./install.sh check` again and report every remaining `warn` or `FAIL`.

Before running these, ask the user: `zsh` runs `chsh` (it needs a password), `packages` uses
`sudo` on Linux, and the user's own instructions outside `## Delegation policy` must stay as
they are.

## Changing this repo

- A component is `components/<name>.sh`. Its first line is `# about: ...`, it sources
  `lib/cfg.sh`, and it must stay idempotent. Add new components to `ALL` and, if needed,
  `DEFAULTS` in `install.sh`.
- Payloads live under `home/` at their install path. Install them with `put <path>`. Merge user
  config with `cfg section`, `cfg defaults`, `cfg omp-settings`, and so on (see `lib/cfg.py`).
  Don't overwrite user config.
- Scripts must work with macOS stock bash 3.2 and `/usr/bin/python3` 3.9, plus apt-based Linux.
- Checks (also run in CI):
  ```sh
  for f in install.sh lib/*.sh components/*.sh; do bash -n "$f"; done
  (cd home/.agents/skills/dissatisfaction && python3 -m unittest test_feedback)
  (cd home/.local/share/cfg-init-feedback && python3 -m unittest test_t3_policy)
  ```
