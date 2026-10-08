---
name: dissatisfaction
description: Score dissatisfaction locally, present explained Yes/No improvement choices, and run approved work in a separate agent.
---

# Personal dissatisfaction feedback

The harness adapter observes each **user** prompt once with a stable event ID. Default `feedback.py submit` returns after a local SQLite write and starts a detached worker; adapters may use `submit --wait` in their own background subprocess. Never wait for scoring or screening before answering the user. Do not submit the worker's own output or screening messages as user prompts.

```sh
printf '%s\n' '{"event_id":"stable-id","session_id":"session-id","prompt":"user text","assistant_context":"optional recent assistant context","cwd":"/worktree"}' | python3 ~/.agents/skills/dissatisfaction/feedback.py submit
python3 ~/.agents/skills/dissatisfaction/feedback.py status stable-id
python3 ~/.agents/skills/dissatisfaction/feedback.py status
python3 ~/.agents/skills/dissatisfaction/feedback.py resolve stable-id 'The user answer'
python3 ~/.agents/skills/dissatisfaction/feedback.py resume stable-id
```

`submit` reads one JSON object from stdin. `event_id`, `session_id`, and `prompt` are required strings. `assistant_context` may be a string or JSON value; `cwd` is an optional string. A repeated `event_id` returns `accepted:false` and does not replace the first event or reprocess it. `resolve EVENT_ID ANSWER` handles clarification (`needs_input`) and review (`proposed`), retaining the original score. The exact answer `approve` also accepts the current `needs_approval` proposal; prefer native choices rather than asking the user to copy IDs. `resume EVENT_ID` retries `failed` or `needs_configuration` after fixing the cause. `status` emits JSON for one event or the 50 most recent; it may restart a dead worker.

The default scorer is `mlx-community/Qwen3-1.7B-4bit` at `http://127.0.0.1:8086/v1`, thinking disabled. One-token YES/NO decoding uses equal logit bias; normalized token likelihoods yield a 0–1 score, not an empirically calibrated probability. `FEEDBACK_THRESHOLD` defaults to `0.8`; screening decides actual actionability above threshold. There is no lexical or fabricated fallback. Invalid output or missing likelihoods remain visible in `status.error`; retries stop after three attempts. Terse reactions can be missed and instruction-like text can score falsely high. Do not equate scores with confirmed complaints.

Override `FEEDBACK_MODEL` and `FEEDBACK_MODEL_URL` (loopback HTTP only) for another backend supporting `logit_bias`, `logprobs` and `top_logprobs`. A different model also requires `FEEDBACK_LABEL_TOKENS`, a JSON object containing distinct single-token IDs for `YES` and `NO`. Default Qwen3 IDs are `{"YES":14004,"NO":8996}`. Verify them against the selected tokenizer; wrong IDs are not a meaningful classifier.

Configure `FEEDBACK_SCREEN_COMMAND` as a JSON array of argv strings, for example `["/absolute/path/to/screen-feedback"]`. No shell is invoked. The worker sends one JSON object to the command's stdin:

```json
{"event_id":"stable-id","session_id":"session-id","phase":"screen","prompt":"user text","assistant_context":"...","cwd":"/worktree","score":0.98,"reason":"local YES/NO normalized token likelihood","actionable":true,"user_answer":null,"approved_proposal":null,"approval_id":null}
```

After `resolve`, `user_answer` contains the answer and screening runs again **without rescoring**. The screening command writes one JSON object with status (`not_actionable`, `needs_input`, `needs_approval`, `proposed`, or `completed`) and a nonempty `summary`. Use `needs_input` only for missing information; a concrete improvement ready for a Yes/No decision uses `needs_approval` with an explanation, question, and evidence. Neither state starts implementation. A `proposed` result contains the separate worker's review-ready report, not proof of completion. Without a configured screener, positive events remain in `needs_configuration`.

State lives in `${XDG_STATE_HOME:-~/.local/state}/cfg-init-feedback` with private directory/database permissions. Input is limited to 64 KiB; prompt to 8,000 characters, assistant context and answers to 2,000 characters. Terminal results discard retained prompt/context; pending proposals remain durable. One file lock serializes workers and screening. Failed calls remain visible and stop after three attempts. A crashed worker can be recovered by `status`; existing implementation worktrees require review instead of automatically replaying work.

The installer merges `FEEDBACK_*` string settings into `~/.config/cfg-init-feedback/config.json`; environment values override defaults. Scoring stays local; the tool-free screener sends positive events to the configured provider.

## Explained approval, separate work

When screening produces `needs_approval`, the harness presents the **proposed change and its reason**, followed by two explicit choices:

* **Yes — work on it separately:** authorize only the displayed proposal. A separate agent inspects and implements in a Git worktree, leaving changes uncommitted for review.
* **No — decline:** close the proposal without starting work.

Closing or cancelling the choice leaves it pending; it is not Yes or No. No complaint, score, or generated text authorizes implementation. Decisions are bound to the event and the current `approval_id`; stale or repeated answers cannot start another worker.

The main conversation stays on its original task. Do not ask it to implement a queued improvement or copy the full conversation into the worker. No automatic installation, push, merge, deployment, or contact is authorized. A separate process/worktree is **not an OS sandbox**.

The OMP interactive extension presents native choices. In T3, the ACP adapter starts a choice-only child agent through T3's supported `delegate_task` interface; that agent presents native Yes/No choices and records the decision, but never performs the improvement itself. `/feedback` recovers pending offers. `/feedback resolve EVENT_ID ANSWER` remains available for clarification and review responses. If the caller-bound T3 transport is unavailable, the queue remains authoritative—do not pretend that it showed a card.

The ACP relay converts T3 scalar `oneOf` choices to equivalent `enum` choices for current T3 compatibility. It leaves other protocol messages unchanged. Caller-bound MCP credentials remain in the host process environment, never in feedback records or task prompts.

Harness adapters use `decide EVENT_ID yes|no --approval-id TOKEN`, not a free-text approval guessed from a chat reply. Never ask the user to copy a long event ID when a native choice is available. The adapters run `submit --wait` in a background subprocess to obtain the screened result for their own event; there is no polling loop, socket broker, or separate presentation daemon. Other ACP harnesses can configure `FEEDBACK_PRESENT_COMMAND` as a JSON argv presenter receiving the public `needs_approval` event on stdin. Without a supported presenter, pending events remain visible through `/feedback`.

`FEEDBACK_IMPLEMENT_COMMAND` optionally selects another harness's independent implementation agent. The command runs inside the new worktree, reads one JSON object on stdin (`phase`, `event_id`, `session_id`, original `cwd`, `approval_id`, frozen `approved_proposal`, and `implementation_worktree`), and returns a JSON object with `status`, nonempty `summary`, and optional `question`/`evidence`. The adapter retains a report and always returns the worktree for review rather than treating the command's success as completion. The default launches a fresh OMP process with extensions, skills, rules, ambient prompts, and session persistence disabled.

`FEEDBACK_SCREEN_TIMEOUT` bounds a screening process to 1–900 seconds (default 180; the installer sets 660 for approved implementation). The OMP interactive adapter observes `input`; T3 uses `omp-feedback acp` to observe raw `session/prompt`. A skill alone cannot guarantee prompt coverage: each harness needs an ingress adapter. Images are not scored. Scoring and screening are separate processes and never gate the main reply.

Pending questions and review-ready proposals invoke optional `FEEDBACK_NOTIFY_COMMAND`, a JSON argv array receiving one bounded text argument. The macOS installer defaults to a native notification; set `""` to disable or `["tg-notify"]` to opt into Telegram. Notification failures remain in the event's error field without replaying screening or implementation. Always retain the durable queue as the fallback when notifications are hidden.
