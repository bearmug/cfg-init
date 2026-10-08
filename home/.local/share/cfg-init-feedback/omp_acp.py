#!/usr/bin/env python3
"""Transparent ACP relay observing session/prompt before command routing."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import uuid


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
    child = subprocess.Popen([real_omp, "acp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=environment)
    pending = {}
    sessions = {}
    last_response = {}
    observations = queue.Queue(maxsize=256)
    lock = threading.Lock()
    output_lock = threading.Lock()
    enabled = environment.get("FEEDBACK_DISABLED") != "1"
    connection_id = str(uuid.uuid4())

    def submitter():
        while True:
            event = observations.get()
            if event is None:
                return
            try:
                result = subprocess.run([sys.executable, str(engine), "submit"], input=json.dumps(event),
                                        text=True, capture_output=True, env=environment, timeout=10)
                if result.returncode:
                    print("feedback enqueue failed: " + result.stderr[-500:], file=sys.stderr, flush=True)
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
        emit({"jsonrpc": "2.0", "method": "session/update", "params": {
            "sessionId": message["params"]["sessionId"], "update": {
                "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": content}}}})
        emit({"jsonrpc": "2.0", "id": message["id"], "result": {"stopReason": "end_turn"}})

    def receive():
        for line in child.stdout:
            # Preserve exact protocol bytes, including unfamiliar extension messages.
            with output_lock:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            try:
                message = json.loads(line)
                with lock:
                    if "id" in message and message["id"] in pending:
                        request = pending.pop(message["id"])
                        result = message.get("result", {})
                        sid = result.get("sessionId") or request.get("sessionId")
                        if sid:
                            sessions[sid] = request.get("cwd", os.getcwd())
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
                with lock:
                    if method in ("session/new", "session/load", "session/resume") and "id" in message:
                        pending[message["id"]] = params
                    if method == "session/prompt":
                        sid = params.get("sessionId", "unknown")
                        text = "\n".join(item.get("text", "") for item in params.get("prompt", [])
                                         if item.get("type") == "text")
                        # T3 wraps user text in an envelope of host instructions.
                        # Score the user request, not injected harness documentation.
                        if text.startswith("<t3_code_instructions>") and "<user_request>" in text:
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
                            if enabled:
                                observations.put_nowait(event)
                        except queue.Full:
                            print("feedback observation queue full; prompt was not scored", file=sys.stderr, flush=True)
                if method == "session/prompt" and (text == "/feedback" or text.startswith("/feedback ")):
                    feedback_command(message, text)
                    continue
            except (ValueError, TypeError, KeyError):
                pass
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
