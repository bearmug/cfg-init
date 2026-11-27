---
name: slow-turn-retro
description: Use after an interactive turn with 10+ minutes of active work, to find and fix recurring slowness in the default path.
---

# Slow-turn retro

Slowness is a bug. After an interactive turn with at least 10 minutes of active work, ask whether it could have been meaningfully faster without losing accuracy, verification, or scope. If so, fix the default path right away: a better CLI default, a cache, config, a parallel or narrower test target, a shared helper, or a guard against a recurring slow command (an interactive prompt missing `-y`, a recursive `grep` over dependency or data directories). Prefer a real fix over an opt-in flag nobody passes or a doc-only note.

Skip the retro when any applies:
- Active work was under 10 minutes. Don't count user waits, approvals, sleeps or timers, or watching CI or logs.
- The run is non-interactive: headless, scheduled, or a subagent task.
- It was thinking-only: the slowest non-file tool call took under 30 seconds.
- The delay was upstream model latency (median model step of 45 seconds or more).

Rules:
- Once per turn. Optimize only what will run again; skip one-off scripts, finished migrations, and irreducible external waits.
- Timebox to about 2–3 minutes. If the change hangs or isn't green by then, revert it and finish.
- Don't take costly, outward-facing, or risky actions without asking.
- Verify the speedup, and record reusable findings in the project's notes.
- Lead the final message with the actual answer; put a one-line `Speedup retro:` note last (or say nothing could safely be sped up).

## Wiring a Stop hook

If a tool exposes a Stop or turn-end hook, a small script can trigger the retro. It measures active time from the last real user prompt, subtracts waits (merging overlapping ones), ignores file read/edit tools when finding the slowest tool, and applies the skip gates. It fires at most once per turn, remembering fired turn ids on disk. It fails open, runs in under 100 ms, does no optimization itself, and logs each fire, skip, and completion to a local JSONL file so the time saved can be checked later. Confirm the tool's transcript format from real sessions before writing a parser.
