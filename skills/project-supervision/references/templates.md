# Optional records

Use existing project records. These are prompts, not four required documents;
combine them and omit irrelevant fields.

## Kickoff

Reuse known answers; ask only the missing decision that changes the next slice.

```text
First user + input/action/visible wow result?
Ranked outcomes, tradeoffs, non-goals?
Delay/noise and platform/data/language/gateway constraints?
Convincing short user flow + existing evidence?
Authority, budget/reserve/fallback/retry limits, escalation/check cadence?
```

## Initiative

Fill before filing; if a line cannot be answered, file a smaller ticket or none.

```text
Existing owner searched (open + recently closed); why not reuse/reopen:
Observable outcome (title) + first user flow it improves:
Smallest slice shipped next; later slices deferred, not pre-filed:
Non-goals / candidate technologies (not the outcome):
Acceptance (<= ~8), each with evidence level + who/what produces it:
User-only evidence/authority owner + when; fallback if unavailable:
Study? decision informed / minimal experiment / threshold / stop date:
Kill or stop criteria; what stays shipped meanwhile:
```

Anti-patterns: day-one spec of every feature; omnibus checklists; "better/robust"
without a threshold; solution- or status-named titles; duplicate lanes for one
outcome; open-ended matrix/replacement programs; acceptance gated on user action
nobody owns; bodies that grow into run logs; scope added without revising
acceptance; deferred or deleted work closed as completed.

## Mission

```text
Revision + user decision sources:
Primary existing ticket + coherent outcome and full acceptance scope (link/ID):
Wow flow / ranked outcomes / tradeoffs / non-goals / constraints:
Observable acceptance + required evidence:
Action authority + source; budget/reserve/model/fallback/retry boundaries:
Worktree/branch/commit/dirty baseline + runtime/build/session:
Integration/resource owners + steering route:
Cross-ticket dependencies + reason:
Top unmet outcome -> action/owner/scope/acceptance/next check:
Unresolved judgment:
```

## Checkpoint

```text
Mission revision/time/identity + evidence references:
Ticket scope changes + ticket update + residual obligations:
User-visible result/failure:
Delivered / missing implementation / missing evidence / explicitly deferred by acceptance item:
Checks run: level/build/input/revisions/coverage/result/limitations:
Observed symptoms / inferred causes:
Bottleneck -> action/owner/scope/acceptance:
Closure status + evidence for every ticket acceptance item:
Executing evidence or waiting reason; budget/reserve; next check:
Stop/resume condition; unknown effects to reconcile:
```

## Handoff

Carry the mission and checkpoint references plus ranked intent/bounds; add only:

```text
Changed decisions + sources; unmet outcomes:
Exact worktree/dirty work/build/session + preserved work/rollback:
Old resource owner + release/verified cessation -> new owner:
Interrupted/unknown-effect calls + reconciliation:
Receiver acknowledgment; read-only probe/identity; first executing action:
Next action/acceptance/check; stop/resume condition:
```
