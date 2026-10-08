---
name: dissatisfaction
description: Score each user prompt locally and queue actionable assistant feedback without blocking the conversation.
---

# Personal dissatisfaction feedback

The harness adapter calls `feedback.py submit` once per **user** prompt with a stable event ID. This CLI returns after a local SQLite write and starts a detached worker. Never wait for scoring or screening before answering the user. Do not submit the worker's own output or screening messages as user prompts.

```sh
printf '%s\n' '{"event_id":"stable-id","session_id":"session-id","prompt":"user text","assistant_context":"optional recent assistant context","cwd":"/worktree"}' | python3 ~/.agents/skills/dissatisfaction/feedback.py submit
python3 ~/.agents/skills/dissatisfaction/feedback.py status stable-id
python3 ~/.agents/skills/dissatisfaction/feedback.py status
python3 ~/.agents/skills/dissatisfaction/feedback.py resolve stable-id 'The user answer'
python3 ~/.agents/skills/dissatisfaction/feedback.py resume stable-id
```

`submit` reads one JSON object from stdin. `event_id`, `session_id`, and `prompt` are required strings. `assistant_context` may be a string or JSON value; `cwd` is an optional string. A repeated `event_id` returns `accepted:false` and does not replace the first event or launch another worker. Keep event IDs unique across sessions. `resolve EVENT_ID ANSWER` works only for `needs_input` or `proposed`; it retains the original score and queues screening again with `user_answer=ANSWER`. `resume EVENT_ID` retries `failed` or `needs_configuration` after fixing the cause. `status` emits JSON for one event or the 50 most recent; it may restart a dead worker.

The default scorer is `mlx-community/Qwen3-1.7B-4bit` at `http://127.0.0.1:8086/v1`, thinking disabled. One-token YES/NO decoding uses equal logit bias; normalized token likelihoods yield a 0–1 score, not an empirically calibrated probability. `FEEDBACK_THRESHOLD` defaults to `0.8`; screening decides actual actionability above threshold. There is no lexical or fabricated fallback. Invalid output or missing likelihoods remain visible in `status.error`; retries stop after three attempts. Terse reactions can be missed and instruction-like text can score falsely high. Do not equate scores with confirmed complaints.

Override `FEEDBACK_MODEL` and `FEEDBACK_MODEL_URL` (loopback HTTP only) for another backend supporting `logit_bias`, `logprobs` and `top_logprobs`. A different model also requires `FEEDBACK_LABEL_TOKENS`, a JSON object containing distinct single-token IDs for `YES` and `NO`. Default Qwen3 IDs are `{"YES":14004,"NO":8996}`. Verify them against the selected tokenizer; wrong IDs are not a meaningful classifier.

Configure `FEEDBACK_SCREEN_COMMAND` as a JSON array of argv strings, for example `["/absolute/path/to/screen-feedback"]`. No shell is invoked. The worker sends one JSON object to the command's stdin:

```json
{"event_id":"stable-id","session_id":"session-id","prompt":"user text","assistant_context":"...","cwd":"/worktree","score":0.98,"reason":"local YES/NO normalized token likelihood","actionable":true,"user_answer":null}
```

After `resolve`, `user_answer` contains the answer and screening runs again **without rescoring**. The command must write one JSON object to stdout with `status` (`not_actionable`, `needs_input`, `proposed`, or `completed`) and a nonempty `summary`. `needs_input` also requires a nonempty `question`. `question` and `evidence` are optional for other states. A `proposed` result should describe the concrete next action and any approval question. The screening command owns its safety checks, isolated followthrough, and event ID based idempotency. The engine never interprets prompt text as executable configuration or edits a checkout by itself. Without a configured screening command, a high scoring event stays in `needs_configuration` until resumed.

State lives in `${XDG_STATE_HOME:-~/.local/state}/cfg-init-feedback` with private directory/database permissions. Input is limited to 64 KiB; prompt to 8,000 characters, assistant context and answers to 2,000 characters. Final `not_actionable` and `completed` events discard retained prompt/context. Pending questions and proposals remain durable. One file lock serializes workers and screening. A failed command or model call enters `retry_wait`, then `failed` after three attempts; inspect `status.error`. Screening commands should handle a repeated `event_id` safely because a process can fail after performing work but before its result is committed.

The installer merges `FEEDBACK_*` string settings into `~/.config/cfg-init-feedback/config.json`; environment values override these defaults. The supplied OMP screener sends positive events to the configured provider, without tools, and records its question. `/feedback` displays the queue in OMP/T3. `/feedback resolve EVENT_ID ANSWER` answers without blocking the main conversation. Only the exact answer `approve` starts a tool-enabled implementation agent in a separate Git worktree; review it before merging. This is not an OS sandbox. No checkout changes, push, merge or deployment are authorized by the score alone.

`FEEDBACK_SCREEN_TIMEOUT` bounds a screening process to 1–900 seconds (default 180; the installer sets 660 for approved implementation). The OMP interactive adapter observes `input`; T3 uses `omp-feedback acp` to observe raw `session/prompt`. A skill alone cannot guarantee prompt coverage: each harness needs an ingress adapter. Images are not scored. Scoring and screening are separate processes and never gate the main reply.

Pending questions and review-ready proposals invoke optional `FEEDBACK_NOTIFY_COMMAND`, a JSON argv array receiving one bounded text argument. The macOS installer defaults to a native notification; set `""` to disable or `["tg-notify"]` to opt into Telegram. Notification failures remain in the event's error field without replaying screening or implementation. Always retain the durable queue as the fallback when notifications are hidden.
