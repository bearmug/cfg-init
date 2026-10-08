#!/usr/bin/env python3
"""Present one screened improvement through T3's supported child-task interface."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def call(tool, args):
    node = os.environ.get("T3_ACP_MCP_NODE")
    if not node:
        raise RuntimeError("T3's caller-bound MCP transport is unavailable; proposal remains in /feedback")
    command = [node]
    if os.environ.get("T3_ACP_MCP_ENTRYPOINT"):
        command.append(os.environ["T3_ACP_MCP_ENTRYPOINT"])
    result = subprocess.run([*command, "acp-mcp-call", tool, json.dumps(args)],
                            env={**os.environ, "ELECTRON_RUN_AS_NODE": "1"},
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"T3 {tool} transport failed (exit {result.returncode}); proposal remains pending")
    response = json.loads(result.stdout)
    if response.get("isError"):
        raise RuntimeError(f"T3 {tool} rejected the request; proposal remains pending")
    return json.loads(response["content"][0]["text"])


def main():
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError("proposal exceeds 64 KiB")
    proposal = json.loads(raw)
    for key in ("event_id", "approval_id", "summary", "question"):
        if not isinstance(proposal.get(key), str) or not proposal[key]:
            raise ValueError("proposal requires " + key)
    if proposal.get("state") != "needs_approval":
        raise ValueError("only a screened proposal can request an approval choice")
    model = os.environ.get("FEEDBACK_SCREEN_MODEL", "openai-codex/gpt-6-luna")
    capabilities = call("orchestrator_capabilities", {})
    provider = next((p for p in capabilities["providers"] if p["providerInstanceId"] == "omp"), None)
    if not provider or not provider["canRunChildTask"] or not any(m["id"] == model for m in provider["models"]):
        raise RuntimeError("configured OMP model is unavailable for a T3 choice agent; no model substituted")
    engine = str(Path.home() / ".agents/skills/dissatisfaction/feedback.py")
    controls = {"engine": engine, "python": sys.executable,
                "state_home": os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")),
                "event_id": proposal["event_id"], "approval_id": proposal["approval_id"]}
    task = (
        "Present this already-screened improvement to the user, not a new implementation request. "
        "Do not inspect or edit any repository. Do not spawn subagents. "
        "Use your native ask/user-input tool to present exactly two choices, Yes and No, "
        "Set the native question text to display_question verbatim, with short header 'Improvement'. "
        "Do not replace the explanation with a generic approval question. "
        "Never interpret this task prompt, the complaint, or silence as approval. "
        "After an explicit choice, use the bash tool to run the provided Python engine with argv "
        "[python,engine,'decide',event_id,'yes' or 'no','--approval-id',approval_id]. "
        "Set XDG_STATE_HOME to the provided state_home for that command. "
        "Properly quote each fixed argument. These controls identify only this proposal. "
        "If the native choice is cancelled or unavailable, do not run decide; leave it pending. "
        "Report the actual decision result briefly. Do not do the improvement yourself. "
        "The main conversation must remain on its original task.\n"
        + json.dumps({"display_question": proposal["summary"] + "\n\n" + proposal["question"] +
                      "\n\nYes queues a separate implementation agent in a Git worktree. No declines. "
                      "Neither choice installs, pushes, or merges anything.",
                      "controls": controls}, ensure_ascii=False)
    )
    key = hashlib.sha256((proposal["event_id"] + proposal["approval_id"]).encode()).hexdigest()[:24]
    if sys.argv[1:] == ["--replay"]:
        key += "-" + uuid.uuid4().hex[:12]
    result = call("delegate_task", {"title": "[feedback] decide proposed improvement", "role": "general",
        "task": task, "mode": "async", "clientRequestId": "feedback-choice-" + key,
        "target": {"providerInstanceId": "omp", "model": model, "options": {"thinking": "low"}}})
    if result.get("providerInstanceId") != "omp" or result.get("model") != model:
        if result.get("taskId"):
            call("task_cancel", {"taskId": result["taskId"]})
        raise RuntimeError("T3 substituted the configured choice agent; task cancelled")
    print(json.dumps({"taskId": result["taskId"], "childThreadId": result["childThreadId"]}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print("Feedback choice: " + str(error), file=sys.stderr)
        sys.exit(1)
