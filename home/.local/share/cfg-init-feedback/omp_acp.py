#!/usr/bin/env python3
"""Transparent ACP relay observing session/prompt before command routing."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid
import t3_policy

QUIET_SECONDS = 120
TICK_SECONDS = 20


def span(seconds):
    """Minute-granular duration so periodic refreshes change the plan at most once a minute."""
    minutes = int(max(0, seconds)) // 60
    if minutes < 1:
        return "<1m"
    return f"{minutes}m" if minutes < 60 else f"{minutes // 60}h{minutes % 60:02d}m"


class SubagentBoard:
    """Append live OMP subagent rows, read from `task` tool progress, to the ACP plan T3 renders."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.todos = {}   # sessionId -> entries from OMP's todo plan
        self.agents = {}  # sessionId -> {(toolCallId, agentId): (progress, receivedAt)}
        self.shown = {}   # sessionId -> entries last sent to T3
        # Sessions replaying history (session/load, session/resume until their response). Stored task
        # results of background spawns hold the spawn-time "pending" snapshot, which would show as ghosts.
        self.replaying = set()

    def observe(self, message):
        """Plan notification to send for this OMP message, or None. Plans always return a merged plan."""
        if message.get("method") != "session/update":
            return None
        params = message.get("params") or {}
        sid, update = params.get("sessionId"), params.get("update") or {}
        kind = update.get("sessionUpdate")
        if kind == "plan":
            self.todos[sid] = [entry for entry in update.get("entries") or [] if isinstance(entry, dict)]
            return self.plan(sid, force=True)
        if kind not in ("tool_call", "tool_call_update"):
            return None
        output = update.get("rawOutput")
        details = output.get("details") if isinstance(output, dict) else None
        progress = details.get("progress") if isinstance(details, dict) else None
        if not isinstance(progress, list) or sid in self.replaying:
            return None
        board = self.agents.setdefault(sid, {})
        now = self.clock()
        for item in progress:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                key = (update.get("toolCallId"), item["id"])
                previous, _, first = board.get(key, (None, now, now))
                # OMP interleaves a stale spawn-time "pending" snapshot after "running".
                if previous and previous.get("status") == "running" and item.get("status") == "pending":
                    item = {**item, "status": "running"}
                board[key] = (item, now, first)
        return self.plan(sid)

    def settle(self, sid):
        """New user prompt: forget finished subagents; running ones stay listed."""
        board = self.agents.get(sid, {})
        for key in [key for key, (item, _, _) in board.items() if item.get("status") not in ("pending", "running")]:
            del board[key]

    def tick(self):
        """Refreshed plans for sessions with live subagents (elapsed time, quiet warnings)."""
        live = [sid for sid, board in self.agents.items()
                if any(item.get("status") in ("pending", "running") for item, _, _ in board.values())]
        return [plan for plan in (self.plan(sid) for sid in live) if plan]

    def row(self, item, received, first):
        now = self.clock()
        status = item.get("status")
        live = status in ("pending", "running")
        facts = []
        if live:
            tool, started = item.get("currentTool"), item.get("currentToolStartMs")
            if tool:
                busy = now - started / 1000 if isinstance(started, (int, float)) and started > 1e12 else None
                facts.append(tool if busy is None else f"{tool} {span(busy)}")
            elif item.get("lastIntent"):
                facts.append(item["lastIntent"])
            if now - received >= QUIET_SECONDS:
                facts.append(f"⚠ quiet {span(now - received)}")
        elif status != "completed":
            facts.append(str(status))
        count = item.get("toolCount", 0)
        facts.append(f"{count} tool" + ("" if count == 1 else "s"))
        # OMP's durationMs lags while a tool runs; for live rows wall time since first sight is truer.
        facts.append(span(now - first if live else (item.get("durationMs") or 0) / 1000 or received - first))
        label = f"⑂ {item['id']} ({item.get('agent', 'agent')})"
        if item.get("description"):
            label += f": {item['description']}"
        return {"content": label + " — " + " · ".join(facts), "priority": "low",
                "status": "completed" if not live else "in_progress" if status == "running" else "pending"}

    def plan(self, sid, force=False):
        entries = self.todos.get(sid, []) + [self.row(*value) for value in self.agents.get(sid, {}).values()]
        if not force and entries == self.shown.get(sid):
            return None
        self.shown[sid] = entries
        return {"jsonrpc": "2.0", "method": "session/update",
                "params": {"sessionId": sid, "update": {"sessionUpdate": "plan", "entries": entries}}}


def t3_choice_enums(message):
    """Expose equivalent scalar enums for T3 versions that do not read oneOf."""
    if message.get("method") != "elicitation/create":
        return False
    properties = message.get("params", {}).get("requestedSchema", {}).get("properties", {})
    changed = False
    for field in properties.values():
        choices = field.get("oneOf")
        if field.get("type") != "string" or "enum" in field or not isinstance(choices, list) or not choices:
            continue
        if all(isinstance(choice, dict) and isinstance(choice.get("const"), str)
               and set(choice) <= {"const", "title", "description", "_meta"} for choice in choices):
            field["enum"] = [choice["const"] for choice in choices]
            del field["oneOf"]
            changed = True
    return changed

def main():
    config_path = Path.home() / ".config/cfg-init-feedback/config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    environment = os.environ.copy()
    for key, value in config.items():
        if key.startswith("FEEDBACK_"):
            environment.setdefault(key, str(value))
    real_omp = environment.get("FEEDBACK_OMP_BIN", "omp")
    environment["FEEDBACK_ACP"] = "1"
    engine = Path.home() / ".agents/skills/dissatisfaction/feedback.py"
    if sys.argv[1:] != ["acp"]:
        os.execv(real_omp, [real_omp, *sys.argv[1:]])
    args = [real_omp, "acp"]
    if environment.get("T3_ACP_MCP_NODE"):
        args += ["--config", str(Path.home() / ".omp/agent/t3.yml")]
    child = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=environment)
    pending = {}
    sessions = {}
    last_response = {}
    observations = queue.Queue(maxsize=256)
    lock = threading.Lock()
    output_lock = threading.Lock()
    enabled = environment.get("FEEDBACK_DISABLED") != "1"
    connection_id = str(uuid.uuid4())
    worker_thread = None
    input_lock = threading.Lock()
    board = SubagentBoard() if environment.get("T3_ACP_MCP_NODE") else None
    board_lock = threading.Lock()

    def send(message):
        with input_lock:
            child.stdin.write(json.dumps(message).encode() + b"\n")
            child.stdin.flush()

    def worker_context():
        nonlocal worker_thread
        if worker_thread is None and environment.get("T3_ACP_MCP_NODE"):
            _, thread, is_worker = t3_policy.context()
            worker_thread = thread if is_worker else False
        return worker_thread

    def submitter():
        while True:
            event = observations.get()
            if event is None:
                return
            try:
                followup = event.get("resolve_event_id")
                if followup:
                    subprocess.run([sys.executable, str(engine), "worker"], env=environment,
                                   check=True, capture_output=True, timeout=900)
                args = ["status", followup] if followup else ["submit", "--wait"]
                result = subprocess.run([sys.executable, str(engine), *args],
                                        input=None if followup else json.dumps(event),
                                        text=True, capture_output=True, env=environment, timeout=900)
                if result.returncode:
                    print("feedback enqueue failed: " + result.stderr[-500:], file=sys.stderr, flush=True)
                else:
                    present(json.loads(result.stdout))
            except Exception as error:
                print("feedback enqueue failed: " + str(error), file=sys.stderr, flush=True)
            finally:
                observations.task_done()

    worker = threading.Thread(target=submitter, daemon=True)
    worker.start()

    def emit(message):
        with output_lock:
            sys.stdout.buffer.write(json.dumps(message).encode() + b"\n")
            sys.stdout.buffer.flush()

    def refresh():
        while True:
            time.sleep(TICK_SECONDS)
            with board_lock:
                plans = board.tick()
            for plan in plans:
                emit(plan)

    if board:
        threading.Thread(target=refresh, daemon=True).start()

    def present(proposal, replay=False):
        if proposal.get("state") != "needs_approval" or worker_context():
            return
        # No choice-only child: the coordinator owns the user decision.
        text = (f"Improvement proposal ({proposal['event_id']}): {proposal['summary']}\n\n"
                f"{proposal['question']}\n"
                "Coordinator: present an explained Yes/No choice here. Never infer consent. "
                "After explicit consent only, run the feedback engine's decide command with "
                f"event_id={proposal['event_id']} and approval_id={proposal['approval_id']}. "
                "Approval queues isolated work; it does not install, push or merge.")
        if environment.get("T3_ACP_MCP_NODE"):
            capabilities, _, _ = t3_policy.context()
            key = f"feedback-coordinator:{proposal['event_id']}:{proposal['approval_id']}"
            if replay:
                key += ":" + uuid.uuid4().hex
            t3_policy.call("t3_thread_send", {"threadId": capabilities["parentThreadId"],
                           "message": text, "mode": "auto", "clientRequestId": key})
            return
        if environment.get("FEEDBACK_PRESENT_COMMAND"):
            command = json.loads(environment["FEEDBACK_PRESENT_COMMAND"])
            if not isinstance(command, list) or not command or any(
                    not isinstance(arg, str) or not arg for arg in command):
                raise ValueError("FEEDBACK_PRESENT_COMMAND must be an argv JSON array")
            subprocess.run(command, input=json.dumps(proposal), env=environment,
                           capture_output=True, text=True, timeout=90, check=True)
            return
        emit({"jsonrpc": "2.0", "method": "session/update", "params": {
            "sessionId": proposal["session_id"], "update": {
                "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}}}})

    def feedback_command(message, text):
        parts = text.split(maxsplit=3)
        if len(parts) == 4 and parts[1] == "resolve":
            args = ["resolve", parts[2], parts[3]]
        elif len(parts) <= 3 and (len(parts) == 1 or parts[1] == "status"):
            args = ["status", *parts[2:]]
        else:
            emit({"jsonrpc": "2.0", "id": message["id"], "error": {
                "code": -32602, "message": "Use /feedback or /feedback resolve EVENT_ID ANSWER"}})
            return
        result = subprocess.run([sys.executable, str(engine), *args], env=environment,
                                capture_output=True, text=True, timeout=10)
        content = result.stdout if result.returncode == 0 else result.stderr
        if result.returncode == 0:
            if args[0] == "resolve":
                observations.put({"resolve_event_id": parts[2]})
            else:
                payload = json.loads(result.stdout)
                proposals = payload.get("events", [payload])
                for proposal in proposals:
                    if proposal.get("session_id") == message["params"]["sessionId"]:
                        present(proposal, replay=True)
        emit({"jsonrpc": "2.0", "method": "session/update", "params": {
            "sessionId": message["params"]["sessionId"], "update": {
                "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": content}}}})
        emit({"jsonrpc": "2.0", "id": message["id"], "result": {"stopReason": "end_turn"}})

    def receive():
        for line in child.stdout:
            # Preserve protocol bytes except equivalent T3 scalar choice enums and subagent plan rows.
            merged = None
            try:
                translated = json.loads(line)
                if worker_thread and translated.get("method") == "elicitation/create":
                    result = {"action": "cancel"}
                    send({"jsonrpc": "2.0", "id": translated["id"], "result": result})
                    emit({"jsonrpc": "2.0", "method": "session/update", "params": {
                        "sessionId": translated.get("params", {}).get("sessionId"),
                        "update": {"sessionUpdate": "agent_message_chunk", "content": {
                            "type": "text", "text": "BLOCKED: child question cancelled; "
                            "coordinator must resolve the missing decision. Security permissions remain host-owned."}}}})
                    continue
                if environment.get("T3_ACP_MCP_NODE") and t3_choice_enums(translated):
                    line = json.dumps(translated).encode() + b"\n"
                if board:
                    with board_lock:
                        merged = board.observe(translated)
                    if merged and translated["params"]["update"]["sessionUpdate"] == "plan":
                        line, merged = json.dumps(merged).encode() + b"\n", None
            except (ValueError, TypeError, AttributeError):
                pass
            with output_lock:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            if merged:
                emit(merged)
            try:
                message = json.loads(line)
                with lock:
                    if "id" in message and message["id"] in pending:
                        request = pending.pop(message["id"])
                        result = message.get("result", {})
                        sid = result.get("sessionId") or request.get("sessionId")
                        if sid:
                            sessions[sid] = request.get("cwd", os.getcwd())
                        if board:
                            with board_lock:
                                board.replaying.discard(request.get("sessionId"))
                    if message.get("method") == "session/update":
                        params = message.get("params", {})
                        update = params.get("update", {})
                        if update.get("sessionUpdate") == "agent_message_chunk":
                            content = update.get("content", {})
                            if content.get("type") == "text":
                                sid = params.get("sessionId")
                                last_response[sid] = (last_response.get(sid, "") + content.get("text", ""))[-4000:]
            except (ValueError, TypeError, KeyError):
                pass

    reader = threading.Thread(target=receive, daemon=True)
    reader.start()
    try:
        for line in sys.stdin.buffer:
            try:
                message = json.loads(line)
                params = message.get("params", {})
                method = message.get("method")
                if method == "session/prompt" and environment.get("T3_ACP_MCP_NODE"):
                    try:
                        thread = worker_context()
                    except Exception as error:
                        emit({"jsonrpc": "2.0", "id": message["id"], "error": {
                            "code": -32000, "message": "Cannot verify T3 lineage; prompt refused: " + str(error)}})
                        continue
                    if thread and (thread.get("runCount") != 1 or sessions.get("_worker_prompt_seen")):
                        emit({"jsonrpc": "2.0", "id": message["id"], "error": {
                            "code": -32000, "message": "Child input disabled; continue through the coordinator with a new task"}})
                        continue
                    if thread:
                        sessions["_worker_prompt_seen"] = True
                        params["prompt"].insert(0, {"type": "text", "text": t3_policy.WORKER_RULES})
                        line = json.dumps(message).encode() + b"\n"
                with lock:
                    if method in ("session/new", "session/load", "session/resume") and "id" in message:
                        pending[message["id"]] = params
                        if board and method != "session/new":
                            with board_lock:
                                board.replaying.add(params.get("sessionId"))
                    if method == "session/prompt":
                        sid = params.get("sessionId", "unknown")
                        if board:
                            with board_lock:
                                board.settle(sid)
                        text = "\n".join(item.get("text", "") for item in params.get("prompt", [])
                                         if item.get("type") == "text")
                        # T3 wraps user text in an envelope of host instructions.
                        # Score the user request, not injected harness documentation.
                        if text.startswith(("<t3_code_instructions>", "<system-reminder>")) and "<user_request>" in text:
                            body = text.split("<user_request>", 1)[1]
                            if "</user_request>" in body:
                                text = body.rsplit("</user_request>", 1)[0].strip()
                        if len(text) > 8000:
                            print("feedback scoring first 2000 and last 6000 characters of long prompt", file=sys.stderr, flush=True)
                            text = text[:2000] + text[-6000:]
                        event = {"event_id": "acp:" + connection_id + ":" + sid + ":" + str(message.get("id", uuid.uuid4())),
                                 "session_id": sid, "prompt": text, "cwd": sessions.get(sid, os.getcwd()),
                                 "assistant_context": last_response.pop(sid, "")[-2000:]}
                        try:
                            if enabled and not worker_thread:
                                observations.put_nowait(event)
                        except queue.Full:
                            print("feedback observation queue full; prompt was not scored", file=sys.stderr, flush=True)
                if method == "session/prompt" and (text == "/feedback" or text.startswith("/feedback ")):
                    feedback_command(message, text)
                    continue
            except (ValueError, TypeError, KeyError):
                pass
            with input_lock:
                child.stdin.write(line)
                child.stdin.flush()
    finally:
        child.stdin.close()
        observations.join()
        reader.join()
        child.wait()
    return child.returncode


if __name__ == "__main__":
    sys.exit(main())
