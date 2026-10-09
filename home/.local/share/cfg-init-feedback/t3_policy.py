#!/usr/bin/env python3
"""Caller-bound T3 routing and ACP worker policy; not a security sandbox."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

SOL = "openai-codex/gpt-6.1-sol"
LUNA = "openai-codex/gpt-6-luna"
WORKER_RULES = (
    "You are a bounded worker, not a coordinator. Do not spawn agents or threads, "
    "including native task/eval agents, T3 delegation, shell-launched agents, or feedback workers. "
    "Do not ask the user or open questions/dialogs. Return missing decisions and permission "
    "requirements as BLOCKED to the coordinator; never infer approval. Do not broaden scope. "
    "Report status, changes/findings, checks actually run, evidence references and blockers."
)


def call(tool, args):
    node = os.environ.get("T3_ACP_MCP_NODE")
    if not node:
        raise RuntimeError("T3 caller-bound MCP transport unavailable")
    command = [node]
    if os.environ.get("T3_ACP_MCP_ENTRYPOINT"):
        command.append(os.environ["T3_ACP_MCP_ENTRYPOINT"])
    result = subprocess.run([*command, "acp-mcp-call", tool, json.dumps(args)],
                            env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"},
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"T3 {tool} failed (exit {result.returncode})")
    response = json.loads(result.stdout)
    if response.get("isError"):
        raise RuntimeError(f"T3 {tool} rejected request")
    return json.loads(response["content"][0]["text"])


def context():
    capabilities = call("orchestrator_capabilities", {})
    thread_id = capabilities["parentThreadId"]  # Caller, despite the historical field name.
    thread = call("t3_thread_read", {"threadId": thread_id, "limit": 1,
                                    "runLimit": 1, "maxCharsPerItem": 1})["thread"]
    if "parentThreadId" not in thread or "relationshipToParent" not in thread:
        raise RuntimeError("T3 did not expose authoritative thread lineage")
    worker = thread["relationshipToParent"] in ("subagent", "delegated_task", "delegated-task")
    # Unknown child lineage is never treated as an unrestricted coordinator.
    if thread["parentThreadId"] and thread["relationshipToParent"] != "fork":
        worker = True
    return capabilities, thread, worker


def select(request, capabilities):
    lane = request.get("lane", "quality")
    if lane not in ("quality", "economy", "pinned"):
        raise ValueError("lane must be quality, economy or pinned")
    reason = request.get("reason", "Safe quality default; consequential ambiguity stays on Sol")
    if lane != "quality" and not request.get("reason", "").strip():
        raise ValueError("economy/pinned routing requires a reason")
    target = {"providerInstanceId": "omp", "model": LUNA if lane == "economy" else SOL,
              "options": {"thinking": "auto", "mode": "default"}}
    if lane == "pinned":
        target = request["target"]
        if not all(target.get(key) for key in ("providerInstanceId", "model")):
            raise ValueError("pins require explicit provider and model")
        if "options" not in target or not isinstance(target["options"], dict):
            raise ValueError("pins require explicit options")
    elif "target" in request:
        raise ValueError("explicit targets require lane=pinned; never silently override a pin")
    provider = next((p for p in capabilities["providers"]
                     if p["providerInstanceId"] == target["providerInstanceId"]), None)
    if not provider or not provider["canRunChildTask"]:
        raise ValueError("selected provider unavailable; no substitution")
    model = next((m for m in provider["models"] if m["id"] == target["model"]), None)
    if not model:
        raise ValueError("selected model unavailable; no substitution")
    definitions = {o["id"]: o for o in model.get("options", [])}
    for key, value in target["options"].items():
        definition = definitions.get(key)
        if not definition or (definition["type"] == "select" and
                              value not in [o["id"] for o in definition["options"]]) or (
                definition["type"] == "boolean" and not isinstance(value, bool)):
            raise ValueError(f"unsupported model option: {key}")
    return target, lane, reason


def audit(record):
    directory = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "cfg-init-t3"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "delegations.jsonl"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **record}) + "\n")


def delegate(request):
    capabilities, thread, worker = context()
    if worker:
        raise ValueError("workers cannot delegate; return BLOCKED to the coordinator")
    for field in ("task", "title", "clientRequestId"):
        if not isinstance(request.get(field), str) or not request[field].strip():
            raise ValueError("required nonempty field: " + field)
    if not request["title"].startswith("[sub] ["):
        raise ValueError("worker title must start with [sub] [topic]")
    target, lane, reason = select(request, capabilities)
    record = {"callerThreadId": thread["threadId"], "clientRequestId": request["clientRequestId"],
              "lane": lane, "reason": reason, "requested": target}
    audit({**record, "status": "requested"})
    result = call("delegate_task", {"task": WORKER_RULES + "\n\n" + request["task"],
                  "title": request["title"], "clientRequestId": request["clientRequestId"],
                  "role": request.get("role", "general"), "target": target, "mode": "async",
                  "runtimeMode": "inherit", "interactionMode": "default"})
    resolved = {"providerInstanceId": result.get("providerInstanceId"), "model": result.get("model")}
    try:
        if any(resolved[key] != target[key] for key in resolved):
            raise RuntimeError("T3 substituted provider/model")
        configuration = call("t3_thread_configuration", {"threadId": result["childThreadId"]})
        selection = configuration["modelSelection"]
        if selection.get("instanceId") != target["providerInstanceId"] or selection.get("model") != target["model"]:
            raise RuntimeError("resolved child configuration differs from request")
        options = selection.get("options", {})
        if isinstance(options, list):
            options = {o["id"]: o["value"] for o in options}
        if any(options.get(key) != value for key, value in target["options"].items()):
            raise RuntimeError("T3 did not confirm requested model options")
    except Exception:
        if result.get("taskId"):
            call("task_cancel", {"taskId": result["taskId"]})
        audit({**record, "status": "cancelled-unverified", "resolved": resolved,
               "taskId": result.get("taskId"), "childThreadId": result.get("childThreadId")})
        raise
    audit({**record, "status": "launched", "resolved": selection,
           "taskId": result["taskId"], "childThreadId": result["childThreadId"]})
    return result


def main():
    if sys.argv[1:] == ["context"]:
        _, thread, worker = context()
        print(json.dumps({"worker": worker, "thread": thread}))
    elif sys.argv[1:] == ["delegate"]:
        raw = sys.stdin.buffer.read(131073)
        if len(raw) > 131072:
            raise ValueError("assignment exceeds 128 KiB")
        print(json.dumps(delegate(json.loads(raw))))
    else:
        raise ValueError("usage: t3_policy.py context|delegate (assignment JSON on stdin)")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print("T3 policy: " + str(error), file=sys.stderr)
        sys.exit(1)
