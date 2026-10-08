"""Deterministic queue/protocol tests. Run with: python3 -m unittest test_feedback.py"""

import contextlib
import importlib.util
import io
import subprocess
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

import feedback


class FakeModel(BaseHTTPRequestHandler):
    model_responses = []
    requests = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.__class__.requests.append(json.loads(body))
        content = self.__class__.model_responses.pop(0)
        response = {"choices": [{"message": {"content": content}}]}
        if isinstance(content, dict):
            response["choices"][0] = content
        elif content in {"YES", "NO"}:
            response["choices"][0]["logprobs"] = {"content": [{"top_logprobs": [
                {"id": 14004, "token": "YES", "logprob": 0 if content == "YES" else -9},
                {"id": 8996, "token": "NO", "logprob": 0 if content == "NO" else -9},
            ]}]}
        encoded = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        pass


class FeedbackTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {
            "XDG_STATE_HOME": self.temp.name,
            "FEEDBACK_MODEL": feedback.DEFAULT_MODEL,
            "FEEDBACK_THRESHOLD": "0.8",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        os.environ["FEEDBACK_MODEL_URL"] = f"http://127.0.0.1:{self.server.server_port}/v1"
        FakeModel.model_responses = []
        FakeModel.requests = []
        self.db = feedback.connect()
        self.addCleanup(self.db.close)

    def enqueue(self, event_id="e1", prompt="You ignored my instructions"):
        event = {"event_id": event_id, "session_id": "s1", "prompt": prompt,
                 "assistant_context": "prior answer", "cwd": self.temp.name}
        with patch.object(feedback, "read_json_stdin", return_value=event), patch.object(feedback, "spawn_worker"):
            return feedback.submit(self.db)

    def row(self, event_id="e1"):
        return self.db.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()

    def make_approval(self, event_id="e1"):
        self.enqueue(event_id)
        self.db.execute(
            """UPDATE events SET state='needs_approval', phase='screen', summary=?, question=?,
               evidence=?, score=0.99, actionable=1 WHERE event_id=?""",
            ("Change the adapter to ask for a clear Yes/No approval.",
             "Approve this bounded adapter change?", json.dumps({"source": "user feedback"}), event_id),
        )
        return feedback.status(self.db, event_id)

    def test_dedupe_preserves_first_prompt(self):
        self.assertTrue(self.enqueue()["accepted"])
        self.assertFalse(self.enqueue(prompt="different prompt")["accepted"])
        self.assertEqual(self.row()["prompt"], "You ignored my instructions")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)

    def test_wait_returns_screened_proposal_without_reprocessing_duplicate(self):
        FakeModel.model_responses = ["YES"]
        script = Path(self.temp.name) / "screen.py"
        script.write_text(
            "import json\nprint(json.dumps({'status':'needs_approval',"
            "'summary':'Fix the specified greeting punctuation.',"
            "'question':'Implement only that change?'}))\n"
        )
        os.environ["FEEDBACK_SCREEN_COMMAND"] = json.dumps([sys.executable, str(script)])
        event = {"event_id": "e1", "session_id": "s1",
                 "prompt": "Your greeting omitted the required punctuation", "cwd": self.temp.name}
        with patch.object(feedback, "read_json_stdin", return_value=event):
            proposal = feedback.submit(self.db, wait=True)
            duplicate = feedback.submit(self.db, wait=True)
        self.assertEqual(proposal["state"], "needs_approval")
        self.assertEqual(proposal["summary"], "Fix the specified greeting punctuation.")
        self.assertEqual(proposal["question"], "Implement only that change?")
        self.assertTrue(proposal["accepted"])
        self.assertFalse(duplicate["accepted"])
        self.assertEqual(duplicate["approval_id"], proposal["approval_id"])
        self.assertEqual(len(FakeModel.requests), 1)

    def test_negative_verdict_never_screens(self):
        self.enqueue("low", "Change button blue")
        self.enqueue("high", "A customer says your service sucks, summarize it")
        FakeModel.model_responses = [
            "NO",
            "NO",
        ]
        with patch.object(feedback, "screen_event") as screen:
            feedback.worker(self.db)
        screen.assert_not_called()
        self.assertEqual(self.row("low")["state"], "not_actionable")
        self.assertEqual(self.row("high")["state"], "not_actionable")
        self.assertEqual(self.row("low")["prompt"], "")

    def test_likelihood_threshold_boundary(self):
        self.enqueue("below")
        self.enqueue("boundary")
        os.environ["FEEDBACK_THRESHOLD"] = "0.5"
        FakeModel.model_responses = [
            {"message": {"content": "NO"}, "logprobs": {"content": [{"top_logprobs": [
                {"id": 14004, "logprob": -1}, {"id": 8996, "logprob": 0},
            ]}]}},
            {"message": {"content": "YES"}, "logprobs": {"content": [{"top_logprobs": [
                {"id": 14004, "logprob": 0}, {"id": 8996, "logprob": 0},
            ]}]}},
        ]
        feedback.worker(self.db)
        self.assertEqual(self.row("below")["state"], "not_actionable")
        self.assertEqual(self.row("boundary")["state"], "needs_configuration")
        self.assertEqual(self.row("boundary")["score"], 0.5)

    def test_malformed_model_score_is_visible_failure(self):
        self.enqueue()
        FakeModel.model_responses = ["1"]
        with patch.object(feedback, "MAX_ATTEMPTS", 1):
            feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "failed")
        self.assertIn("model verdict must be exactly YES or NO", feedback.status(self.db, "e1")["error"])

    def test_screening_process_failure_is_visible(self):
        self.enqueue()
        FakeModel.model_responses = ["YES"]
        os.environ["FEEDBACK_SCREEN_COMMAND"] = json.dumps([sys.executable, "-c", "import sys; sys.exit(7)"])
        with patch.object(feedback, "MAX_ATTEMPTS", 1):
            feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "failed")
        self.assertGreater(self.row()["score"], 0.99)
        self.assertIn("exited 7", self.row()["error"])

    def test_notification_failure_does_not_replay_screening(self):
        self.enqueue()
        FakeModel.model_responses = ["YES"]
        record = Path(self.temp.name) / "screened.txt"
        script = Path(self.temp.name) / "screen.py"
        script.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "with Path(sys.argv[1]).open('a') as f: f.write('screened\\n')\n"
            "print(json.dumps({'status':'needs_input','summary':'Targeted fix','question':'Approve?'}))\n"
        )
        os.environ["FEEDBACK_SCREEN_COMMAND"] = json.dumps([sys.executable, str(script), str(record)])
        os.environ["FEEDBACK_NOTIFY_COMMAND"] = json.dumps([sys.executable, "-c", "import sys; sys.exit(7)"])
        feedback.worker(self.db)
        feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "needs_input")
        self.assertEqual(self.row()["question"], "Approve?")
        self.assertIn("NotificationError", self.row()["error"])
        self.assertEqual(record.read_text(), "screened\n")

    def test_prompt_cannot_become_command_and_resolve_does_not_rescore(self):
        marker = Path(self.temp.name) / "should-not-exist"
        malicious = f"You ignored me; $(touch {marker})"
        self.enqueue(prompt=malicious)
        FakeModel.model_responses = ["YES"]
        feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "needs_configuration")
        self.assertFalse(marker.exists())

        capture = Path(self.temp.name) / "screen-input.jsonl"
        script = Path(self.temp.name) / "screen.py"
        script.write_text(
            "import json,sys\n"
            "from pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            "with Path(sys.argv[1]).open('a') as f: f.write(json.dumps(data)+'\\n')\n"
            "if data['user_answer'] is None:\n"
            " print(json.dumps({'status':'needs_input','summary':'Need details','question':'Which file?'}))\n"
            "elif data['user_answer']=='details':\n"
            " print(json.dumps({'status':'proposed','summary':'Isolated change ready','question':'Approve?'}))\n"
            "else:\n"
            " print(json.dumps({'status':'completed','summary':'Approved change done'}))\n"
        )
        os.environ["FEEDBACK_SCREEN_COMMAND"] = json.dumps([sys.executable, str(script), str(capture)])
        with patch.object(feedback, "spawn_worker"):
            feedback.resume(self.db, "e1")
        feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "needs_input")
        self.assertEqual(self.row()["question"], "Which file?")
        with patch.object(feedback, "spawn_worker"):
            feedback.resolve(self.db, "e1", "details")
        feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "proposed")
        with patch.object(feedback, "spawn_worker"):
            feedback.resolve(self.db, "e1", "approved")
        feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "completed")
        self.assertEqual(len(FakeModel.requests), 1)
        inputs = [json.loads(line) for line in capture.read_text().splitlines()]
        self.assertEqual([entry["user_answer"] for entry in inputs], [None, "details", "approved"])
        self.assertTrue(all(entry["event_id"] == "e1" for entry in inputs))
        self.assertTrue(all(entry["prompt"] == malicious for entry in inputs))
        self.assertFalse(marker.exists())
        self.assertEqual(self.row()["prompt"], "")

    def test_yes_no_cancel_stale_and_duplicate_approval_safety(self):
        proposal = self.make_approval()
        self.assertEqual(proposal["cwd"], self.temp.name)
        self.assertTrue(proposal["approval_id"].startswith("apv_"))
        self.assertEqual(proposal["state"], "needs_approval")
        with patch.object(feedback, "spawn_worker") as spawn:
            with self.assertRaisesRegex(ValueError, "yes or no"):
                feedback.decide(self.db, "e1", "cancel", proposal["approval_id"])
            self.assertEqual(self.row()["state"], "needs_approval")
            with self.assertRaisesRegex(ValueError, "stale or invalid"):
                feedback.decide(self.db, "e1", "yes", "apv_stale")
            self.assertEqual(self.row()["state"], "needs_approval")
            self.assertEqual(spawn.call_count, 0)

            feedback.decide(self.db, "e1", "no", proposal["approval_id"])
            self.assertEqual(self.row()["state"], "declined")
            self.assertEqual(self.row()["prompt"], "")
            self.assertEqual(self.row()["assistant_context"], "")
            with self.assertRaisesRegex(ValueError, "stale or duplicated"):
                feedback.decide(self.db, "e1", "yes", proposal["approval_id"])
            self.assertEqual(spawn.call_count, 0)

        approved = self.make_approval("e2")
        with patch.object(feedback, "spawn_worker") as spawn:
            feedback.decide(self.db, "e2", "yes", approved["approval_id"])
            self.assertEqual(self.row("e2")["phase"], "implement")
            self.assertEqual(self.row("e2")["state"], "queued")
            self.assertEqual(spawn.call_count, 1)
            with self.assertRaisesRegex(ValueError, "stale or duplicated"):
                feedback.decide(self.db, "e2", "yes", approved["approval_id"])
            self.assertEqual(spawn.call_count, 1)

    def test_approved_proposal_snapshot_is_sent_to_implementation_phase(self):
        proposal = self.make_approval()
        with patch.object(feedback, "spawn_worker"):
            feedback.decide(self.db, "e1", "yes", proposal["approval_id"])
        capture = Path(self.temp.name) / "implement-input.json"
        script = Path(self.temp.name) / "screen.py"
        script.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\nPath(sys.argv[1]).write_text(json.dumps(data))\n"
            "print(json.dumps({'status':'completed','summary':'implementation handed off'}))\n"
        )
        result = feedback.screen_event(self.row(), [sys.executable, str(script), str(capture)])
        sent = json.loads(capture.read_text())
        self.assertEqual(sent["phase"], "implement")
        self.assertEqual(sent["user_answer"], "approve")
        self.assertEqual(sent["approval_id"], proposal["approval_id"])
        self.assertEqual(sent["approved_proposal"]["summary"], proposal["summary"])
        self.assertEqual(sent["approved_proposal"]["question"], proposal["question"])
        self.assertEqual(sent["approved_proposal"]["evidence"], proposal["evidence"])
        self.assertEqual(result["status"], "completed")

    def test_screen_distinguishes_missing_details_from_approval(self):
        self.enqueue()
        script = Path(self.temp.name) / "screen.py"
        script.write_text(
            "import json,sys\n"
            "print(sys.argv[1])\n"
        )
        command = [sys.executable, str(script),
                   json.dumps({"status": "needs_input", "summary": "Need the target path", "question": "Which file?"})]
        self.assertEqual(feedback.screen_event(self.row(), command)["status"], "needs_input")
        command[2] = json.dumps({"status": "needs_approval", "summary": "Update the response adapter to explain the change.",
                                 "question": "Approve this bounded change?"})
        self.assertEqual(feedback.screen_event(self.row(), command)["status"], "needs_approval")
        command[2] = json.dumps({"status": "needs_approval", "summary": " ", "question": "Approve?"})
        with self.assertRaisesRegex(ValueError, "summary"):
            feedback.screen_event(self.row(), command)

    def test_legacy_resolve_literal_approve_uses_checked_approval_transition(self):
        proposal = self.make_approval()
        with patch.object(feedback, "spawn_worker") as spawn:
            feedback.resolve(self.db, "e1", "approve")
        row = self.row()
        self.assertEqual(row["phase"], "implement")
        self.assertEqual(row["approved_summary"], proposal["summary"])
        self.assertEqual(row["approval_id"], proposal["approval_id"])
        self.assertEqual(spawn.call_count, 1)



class AcpRelayTest(unittest.TestCase):
    def test_t3_native_choices_preserve_the_approved_value_domain(self):
        relay = Path(__file__).resolve().parents[3] / ".local/share/cfg-init-feedback/omp_acp.py"
        spec = importlib.util.spec_from_file_location("omp_acp", relay)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        choices = [{"const": "Yes", "title": "Approve", "description": "Queue separate work."},
                   {"const": "No", "title": "Decline", "description": "Do not queue work."}]
        message = {"method": "elicitation/create", "params": {"requestedSchema": {
            "properties": {"decision": {"type": "string", "oneOf": choices},
                           "comment": {"type": "string"},
                           "multi": {"type": "array", "items": {"oneOf": choices}}}}}}
        self.assertTrue(adapter.t3_choice_enums(message))
        fields = message["params"]["requestedSchema"]["properties"]
        self.assertEqual(fields["decision"]["enum"], ["Yes", "No"])
        self.assertNotIn("oneOf", fields["decision"])
        self.assertNotIn("enum", fields["comment"])
        self.assertNotIn("enum", fields["multi"])
        self.assertFalse(adapter.t3_choice_enums(message))

    def test_host_envelope_is_not_scored_and_feedback_stays_local(self):
        relay = Path(__file__).resolve().parents[3] / ".local/share/cfg-init-feedback/omp_acp.py"
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            engine = home / ".agents/skills/dissatisfaction/feedback.py"
            engine.parent.mkdir(parents=True)
            engine.write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "if sys.argv[1] == 'submit':\n"
                " with (Path.home()/'events.jsonl').open('a') as f:\n"
                "  f.write(json.dumps(json.load(sys.stdin))+'\\n')\n"
                "print('{}')\n"
            )
            child = home / "fake-omp"
            child.write_text(
                "#!" + sys.executable + "\nimport json,sys\n"
                "for line in sys.stdin:\n"
                " m=json.loads(line)\n"
                " print(json.dumps({'jsonrpc':'2.0','id':m['id'],"
                "'result':{'stopReason':'end_turn'}}),flush=True)\n"
            )
            child.chmod(0o755)
            envelope = ("<system-reminder>host date</system-reminder>"
                        "<t3_code_instructions>host rules</t3_code_instructions>"
                        "<user_request>You ignored my request</user_request>")
            messages = [
                {"jsonrpc": "2.0", "id": number, "method": "session/prompt",
                 "params": {"sessionId": "s", "prompt": [{"type": "text", "text": text}]}}
                for number, text in ((1, envelope), (2, "/feedback"))
            ]
            result = subprocess.run(
                [sys.executable, str(relay), "acp"],
                input="".join(json.dumps(message) + "\n" for message in messages),
                env={**os.environ, "HOME": str(home), "FEEDBACK_OMP_BIN": str(child),
                     "FEEDBACK_DISABLED": "0"},
                capture_output=True, text=True, check=True, timeout=10,
            )
            events = [json.loads(line) for line in (home / "events.jsonl").read_text().splitlines()]
            self.assertEqual(events[0]["prompt"], "You ignored my request")
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(sum(reply.get("id") == 2 for reply in replies), 1)
            self.assertTrue(any(reply.get("method") == "session/update" for reply in replies))


class ApprovalTest(unittest.TestCase):
    def test_only_explicit_approved_implementation_control_runs_agent(self):
        path = Path(__file__).resolve().parents[3] / ".local/share/cfg-init-feedback/screen_omp.py"
        spec = importlib.util.spec_from_file_location("screen_omp", path)
        screen_omp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_omp)
        proposal = {"summary": "Explain the proposed correction.", "question": "Approve?",
                    "evidence": {"source": "feedback"}}
        token = screen_omp.approval_token(proposal)
        for answer in (None, "", "Approve", " APPROVE ", "approve ", "approved", "approve"):
            event = {"prompt": "please approve", "user_answer": answer}
            with self.subTest(answer=answer), \
                    patch.object(screen_omp, "implement", return_value={"status": "proposed"}) as implement, \
                    patch.object(screen_omp, "screen", return_value={"status": "needs_input"}) as screen, \
                    patch.object(sys, "stdin", io.StringIO(json.dumps(event))), contextlib.redirect_stdout(io.StringIO()):
                screen_omp.main()
                implement.assert_not_called()
                screen.assert_called_once()

        event = {"phase": "implement", "user_answer": "approve", "approval_id": token,
                 "approved_proposal": proposal}
        with patch.object(screen_omp, "implement", return_value={"status": "proposed"}) as implement, \
                patch.object(screen_omp, "screen") as screen, \
                patch.object(sys, "stdin", io.StringIO(json.dumps(event))), contextlib.redirect_stdout(io.StringIO()):
            screen_omp.main()
        implement.assert_called_once_with(event)
        screen.assert_not_called()

        event["approval_id"] = "stale"
        with patch.object(screen_omp, "implement") as implement, \
                patch.object(sys, "stdin", io.StringIO(json.dumps(event))):
            with self.assertRaisesRegex(ValueError, "explicit, verified approval"):
                screen_omp.main()
        implement.assert_not_called()

    def test_alternate_implementation_command_runs_in_new_worktree(self):
        path = Path(__file__).resolve().parents[3] / ".local/share/cfg-init-feedback/screen_omp.py"
        spec = importlib.util.spec_from_file_location("screen_omp", path)
        screen_omp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(screen_omp)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            (root / "README.md").write_text("seed\n")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-m", "seed"],
                           check=True, capture_output=True)
            state = Path(directory) / "state"
            command = Path(directory) / "implement.py"
            command.write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "data=json.load(sys.stdin)\nPath('isolated.txt').write_text(data['approved_proposal']['summary'])\n"
                "print(json.dumps({'status':'completed','summary':'wrote isolated change'}))\n"
            )
            proposal = {"summary": "Only the approved adjustment", "question": "Approve?",
                        "evidence": {"line": 1}}
            event = {"phase": "implement", "event_id": "isolated-test", "session_id": "s",
                     "cwd": str(root), "user_answer": "approve", "approved_proposal": proposal,
                     "approval_id": screen_omp.approval_token(proposal)}
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(state),
                                         "FEEDBACK_IMPLEMENT_COMMAND": json.dumps([sys.executable, str(command)])}):
                result = screen_omp.implement(event)
            worktree = Path(result["evidence"]["worktree"])
            self.assertTrue((worktree / "isolated.txt").exists())
            self.assertFalse((root / "isolated.txt").exists())


if __name__ == "__main__":
    unittest.main()
