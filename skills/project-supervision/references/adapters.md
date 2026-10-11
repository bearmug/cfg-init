# Capability mappings

Map roles to existing capabilities; these are not required APIs.

| | A. Command harness | B. Periodic records supervisor |
|---|---|---|
| Observe | Records, Git status/diff, commands, build/session identity | Executor checkpoint, referenced evidence, timestamped build/session report |
| Steer | Same run or existing task channel | One instruction in agreed durable inbox |
| Execute/resume | Authorized commands in owned scope | Unavailable; executor consumes inbox at next invocation/safe checkpoint |
| Verify | Relevant authorized user-flow check | Read referenced results; missing/stale evidence remains unverified |
| Persist/report | Existing records/conversation | Latest checkpoint and existing delivery route; notify on decision, blocker, meaningful outcome within mission limits |
| Next check | Slice boundary or already-provisioned invocation | Existing periodic invocation |

In B, executor acknowledges the instruction separately from execution. Without
an executor that consumes it, record waiting: no delivery/resume capability.
Use an authorized existing controller or ask once for the missing capability.
Do not overwrite an unacknowledged instruction; reconcile or supersede it at a
safe boundary. Writing an inbox cannot prove execution or promise continuous control.

Ownership enforcement must be observable (existing lock/sole-writer coordination);
a name in a record is advisory. Process existence/log growth alone cannot prove
useful progress, nor can a passing command prove a different installed build works.

Native task tools can map to the same contracts. For optional workers in cfg-init,
reuse the compatible [delegation policy](../../../home/.omp/agent/APPEND_SYSTEM.md);
translate native batching to the selected harness. No new scheduler or global
preprompt is implied.
