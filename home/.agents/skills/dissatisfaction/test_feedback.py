"""Deterministic queue/protocol tests. Run with: python3 -m unittest test_feedback.py"""

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
    responses = []
    requests = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.__class__.requests.append(json.loads(body))
        content = self.__class__.responses.pop(0)
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
        FakeModel.responses = []
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

    def test_dedupe_preserves_first_prompt(self):
        self.assertTrue(self.enqueue()["accepted"])
        self.assertFalse(self.enqueue(prompt="different prompt")["accepted"])
        self.assertEqual(self.row()["prompt"], "You ignored my instructions")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)

    def test_negative_verdict_never_screens(self):
        self.enqueue("low", "Change button blue")
        self.enqueue("high", "A customer says your service sucks, summarize it")
        FakeModel.responses = [
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
        FakeModel.responses = [
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
        FakeModel.responses = ["1"]
        with patch.object(feedback, "MAX_ATTEMPTS", 1):
            feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "failed")
        self.assertIn("model verdict must be exactly YES or NO", feedback.status(self.db, "e1")["error"])

    def test_screening_process_failure_is_visible(self):
        self.enqueue()
        FakeModel.responses = ["YES"]
        os.environ["FEEDBACK_SCREEN_COMMAND"] = json.dumps([sys.executable, "-c", "import sys; sys.exit(7)"])
        with patch.object(feedback, "MAX_ATTEMPTS", 1):
            feedback.worker(self.db)
        self.assertEqual(self.row()["state"], "failed")
        self.assertGreater(self.row()["score"], 0.99)
        self.assertIn("exited 7", self.row()["error"])

    def test_notification_failure_does_not_replay_screening(self):
        self.enqueue()
        FakeModel.responses = ["YES"]
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
        FakeModel.responses = ["YES"]
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


if __name__ == "__main__":
    unittest.main()
