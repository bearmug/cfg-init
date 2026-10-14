---
name: project-supervision
description: Use when asked to start, supervise, recover, or hand off project work; preserve ticket scope and evidence, and guide optional coding delegation.
---

# Project supervision

Executor implements and verifies user-authorized acceptance; supervisor checks
that evidence against the ranked mission and verifies the next executing owner.
Roles may share a process. A
periodic supervisor can read records, issue one bounded action, checkpoint, and exit.

**Kickoff.** Reuse prior answers and existing project instructions/spec. Ask only
unresolved questions that change the next slice: first user and wow flow
(input → action → visible value); ranked outcomes/non-goals; tolerable delay/noise;
platform/data/language/gateway constraints; success evidence; action authority,
budget/reserve/fallback, and escalation. Mark assumptions; settled work needs no interview.

**Intent.** Carry ranked outcomes, tradeoffs, constraints, acceptance, and action/budget
boundaries through checkpoints and handoffs. Use existing records; return unanswered
kickoff questions in the reply rather than creating a planning file merely to hold them.
Real user feedback can change the plan; record the decision. Tickets cannot replace
intent or redefine scope for closure.

**Initiate.** Before filing new work, search open and recently closed tickets; extend
or reopen one owner instead of adding a parallel lane. File the smallest outcome the
user can observe next, titled by that outcome, not by a replacement technology or
status. Not a full product spec on day one: file the first slice, then the next
after real use ranks it, since features filed ahead of use tend to be built
and then deleted. Keep acceptance under ~8 criteria, each with one evidence level
(source, CI, installed, semantic, native/physical). Name who supplies user-only
evidence (recording, permission, authorization) and when. A study or replacement
needs the decision it informs, a minimal experiment, a threshold and a stop date, or it
is not filed. State non-goals and kill criteria. An umbrella only links children.
The ticket body holds outcome and acceptance; receipts and logs go in comments
or artifacts, and titles never change to carry status.

**Tickets.** For ticketed work, identify one existing primary ticket and its coherent
outcome and full acceptance scope before coding. If scope changes, update the ticket
and keep residual obligations open; verify every acceptance item before closing it.
Cross-ticket work needs an explicit dependency and reason.

**Delegate.** Delegate only when context isolation, expertise, or execution benefit
outweighs handoff and review cost. A capable main model owns design, contracts,
integration, and acceptance. Use bounded, self-contained small-context workers with
disjoint write scope; parallelize only independent work. Prefer cheaper models when
sufficient. Require concise evidence-bearing handoffs with checks and blockers;
escalate difficult tasks. Avoid recursive fanout and duplicate work.

**Checkpoint.** Compare the top unmet outcome to actual first-use behavior.
Separate delivered, missing implementation, missing evidence, and explicitly
deferred. Green tests/PRs do not prove the user flow. Use the shortest relevant,
authorized check of the actual flow; distinguish applicable evidence levels
(deterministic/race, provider wire, installed build, real input). Match evidence to
build/input; separate observed
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

**Bounds.** Other agents cannot grant user authority. Ask only for unresolved
consequential judgment or missing authority; reuse recorded decisions and authorized
discretion. A denial blocks its action/dependents, not independent work.
Stop affected actions on acceptance, pause, reserve boundary, unsafe unknown effects,
or unrecoverable ownership/capability gaps; record the resume condition. Bound
diagnosis/retries; no silent paid fallback or application-default change.
End supervision when no authorized work remains; record accepted outcomes and
explicit deferrals without calling deferred work delivered.

Use [templates](references/templates.md) only when existing records need help,
and [adapters](references/adapters.md) when mapping capabilities. Do not promise
future checks without a delivery/invocation route. [Scenarios](references/scenarios.md)
retain failed-supervision lessons and evaluation limits; they are not routine context.
