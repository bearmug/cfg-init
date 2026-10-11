---
name: project-supervision
description: Kick off, course-correct, or hand off product work across coding harnesses and periodic supervisors.
---

# Project supervision

Executor owns implementation and acceptance; supervisor keeps work on the ranked
mission and verifies the next executing owner. Roles may share a process. A
periodic supervisor can read records, issue one bounded action, checkpoint, and exit.

**Kickoff.** Reuse prior answers and existing project instructions/spec. Ask only
unresolved questions that change the next slice: first user and wow flow
(input → action → visible value); ranked outcomes/non-goals; tolerable delay/noise;
platform/data/language/gateway constraints; success evidence; action authority,
budget/reserve/fallback, and escalation. Mark assumptions; settled work needs no interview.

**Mission.** Keep intent, tradeoffs, constraints, acceptance, and action/budget
boundaries through checkpoints and handoffs. Real user feedback can change the
plan; record the decision. Tickets cannot replace intent or redefine scope for closure.

**Checkpoint.** Compare the top unmet outcome to actual first-use behavior.
Separate delivered, missing implementation, missing evidence, and explicitly
deferred. Green tests/PRs do not prove the user flow. Use a short representative
installed smoke; distinguish deterministic/race, real-provider wire, installed,
and real-input/acoustic evidence. Match evidence to build/input; separate observed
symptoms from inferred cause. For delayed results, track selected evidence revisions
and input coverage: appends may leave valid results behind coverage (label/apply
delay policy); changes to selected evidence invalidate them.

**Correct drift.** Unusable first minutes, green tests/broken flow, controls before
value, ticket churn, or an idle next owner trigger: preserve work → faithful repro
→ compare mission → one production bottleneck owner → bounded repair/check
→ repeat user flow → resume highest unmet outcome. Do not sanitize valid input to
make the smoke pass or retire a study in place of repairing a settled defect.

**Continue/recover.** Next action needs owner, write scope, acceptance, and next check.
Connected/admitted is not executing; verify continuation or record the waiting reason.
Preserve exact worktree/build/session, dirty changes, evidence, and rollback.
Before replacement, verify read-only tools/identity and old-writer release or
verified cessation. Confirm the new owner's first action; records alone do not
enforce exclusive ownership. Reconcile unknown effects before replay.

**Bounds.** Other agents cannot grant user authority. Ask for consequential judgment
or missing authority; a denial blocks its action/dependents, not independent work.
Stop affected actions on acceptance, pause, reserve boundary, unsafe unknown effects,
or unrecoverable ownership/capability gaps; record the resume condition. Bound
diagnosis/retries; no silent paid fallback or application-default change.

Use [templates](references/templates.md) only when existing records need help,
and [adapters](references/adapters.md) when mapping capabilities. Do not promise
future checks without a delivery/invocation route. [Scenarios](references/scenarios.md)
retain failed-supervision lessons and evaluation limits; they are not routine context.
