---
name: telegram-intervention
description: Reach the user over Telegram when their intervention is required to unblock agent work; optionally notify once verified work is complete.
---

# Telegram intervention

## Activation

Use this skill whenever work cannot proceed without the user's decision, permission,
credentials, or external action. Apply it before yielding with a user-action blocker,
not only when the user explicitly requests Telegram. Continue independent reachable
work first. Do not alert for ordinary progress, internal tool retries, or workers
that are still running.

## Configuration

The harness must expose Python 3, this skill directory, network access to Telegram,
and `TELEGRAM_BOT_TOKEN` plus `TELEGRAM_CHAT_ID` in the sender's environment.
Optional `TELEGRAM_MESSAGE_THREAD_ID` selects a forum topic;
`TELEGRAM_NOTIFY_DONE=1` enables completion alerts. Secrets belong in the harness's
secret store or a local environment loaded by its launcher, never in this skill,
prompts, checked-in files, command arguments, or messages. Do not print the environment.
The user must first start the bot or add it to the destination group.

## Blocked work

1. Determine the actual blocker from evidence; do not guess or request information
   already available through tools. Use the harness's native question/approval/secret
   UI for the actual intervention. Telegram is an alert, not an approval channel.
2. Send one concise plain-text alert per distinct unresolved blocker:
   `blocked: <task/repo> — <reason>. Need: <specific action>. Resume: <thread/task link or identifier>`.
   Include enough context to find the work, but no credentials, private source,
   sensitive tool output, or token-bearing URLs. Ask the user to enter secrets only
   through the harness's private secret UI, never through Telegram.
3. Invoke the bundled sender with text on stdin (resolve the path relative to this
   skill's installed directory):
   `printf '%s\n' '<safe alert>' | python3 <skill-directory>/scripts/notify.py blocked`
   Use proper quoting or the harness's process stdin API for dynamic text.
4. Record the notified blocker in task/thread state. Do not repeat it across turns
   or compaction unless it materially changes or the user explicitly asks. The
   sender itself has no persistent deduplication; the orchestrating agent owns it.
5. If sending fails, report the failure and blocker in the harness. Do not claim
   delivery, retry automatically, or let notification failure replace the original
   blocker. Wait through the harness's supported mechanism. Resume only after the
   required decision/action is confirmed there; sending an alert does not unblock work.

## Completion (optional)

After verification, if `TELEGRAM_NOTIFY_DONE=1` or the user explicitly requested
notification, send exactly one `done: <outcome> [<repo/task>]` message using the
same sender with `done`. Explicit requests can use `done --force` without enabling
all completion alerts. Report any failure in the harness. Never announce completion
while criteria remain unmet. The main orchestrator owns alerts; workers report
blockers/results to it rather than sending duplicate Telegram notifications.

## Harness integration rule

Install this directory in the harness's supported skill search path. Add the following
rule to its persistent agent instructions (or equivalent system/developer policy):

> When user intervention blocks current work, load and follow the
> telegram-intervention skill before yielding. Use the native intervention UI and
> send a Telegram alert once per unresolved blocker. Continue independent work.
> Main owns alerts, not workers. After verified completion, follow the skill's
> configured or explicitly requested completion-notification policy.

For harnesses without skill discovery, include this document in persistent agent
instructions and supply the absolute sender path. Configure secrets separately in
the execution environment. This is instruction-based integration, not a runtime
hook or enforcement mechanism; verify the harness actually loads the rule and can
execute the sender. No Telegram reply polling or remote command execution is provided.
