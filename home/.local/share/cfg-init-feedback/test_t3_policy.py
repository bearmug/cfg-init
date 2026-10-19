"""Behavioral routing and ACP boundary tests; no live provider or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["T3_QUOTA"] = "off"  # Never read real `omp usage` here; see test_quota.py.
import t3_policy as policy  # noqa: E402

SOL = policy.TIERS[policy.DEFAULT_LANE]
LUNA = policy.TIERS["easy-luna"]


def catalog():
    options = [{"id": "thinking", "type": "select", "options": [{"id": "auto"}, {"id": "high"}]},
               {"id": "mode", "type": "select", "options": [{"id": "default"}]}]
    return {"parentThreadId": "parent", "providers": [{"providerInstanceId": "omp", "canRunChildTask": True,
            "models": [{"id": m, "options": options} for m in policy.TIERS.values()]}]}


class RoutingTest(unittest.TestCase):
    def test_tier_lanes_and_pins_do_not_override_default_silently(self):
        self.assertEqual(policy.select({}, catalog())[0]["model"], SOL)
        self.assertEqual(policy.select({"lane": "easy-haiku", "reason": "bounded extraction"}, catalog())[0]["model"],
                         policy.TIERS["easy-haiku"])
        for request in ({"lane": "easy-luna"}, {"lane": "economy", "reason": "retired lane"}, {"target": {"model": LUNA}},
                        {"lane": "pinned", "reason": "user pin", "target": {
                            "providerInstanceId": "omp", "model": SOL, "options": {"thinking": "xhigh"}}}):
            with self.subTest(request=request), self.assertRaises(ValueError):
                policy.select(request, catalog())
        target = {"providerInstanceId": "omp", "model": SOL, "options": {"thinking": "high"}}
        self.assertEqual(policy.select({"lane": "pinned", "reason": "user explicitly pinned high", "target": target}, catalog())[0], target)
        missing = catalog()
        missing["providers"][0]["models"] = []
        with self.assertRaisesRegex(ValueError, "no substitution"):
            policy.select({}, missing)

    def test_worker_cannot_launch_and_substitution_cancels_not_accepts(self):
        assignment = {"task": "Inspect bounded issue", "title": "[sub] [routing] inspect issue", "clientRequestId": "round1"}
        with patch.object(policy, "context", return_value=(catalog(), {"threadId": "child"}, True)), \
                patch.object(policy, "call") as call:
            with self.assertRaisesRegex(ValueError, "workers cannot delegate"):
                policy.delegate(assignment)
            call.assert_not_called()
        calls = []
        def transport(tool, args):
            calls.append((tool, args))
            if tool == "delegate_task":
                return {"taskId": "task", "childThreadId": "child", "providerInstanceId": "omp", "model": LUNA}
            return {}
        with patch.object(policy, "context", return_value=(catalog(), {"threadId": "parent"}, False)), \
                patch.object(policy, "call", side_effect=transport), patch.object(policy, "audit"):
            with self.assertRaisesRegex(RuntimeError, "substituted"):
                policy.delegate(assignment)
        self.assertEqual(calls[-1], ("task_cancel", {"taskId": "task"}))

    def test_unconfirmed_thinking_cancels_even_when_model_matches(self):
        def transport(tool, args):
            if tool == "delegate_task":
                return {"taskId": "task", "childThreadId": "child", "providerInstanceId": "omp", "model": SOL}
            if tool == "t3_thread_configuration":
                return {"modelSelection": {"instanceId": "omp", "model": SOL, "options": [{"id": "thinking", "value": "low"}]}}
            return {}
        with patch.object(policy, "context", return_value=(catalog(), {"threadId": "parent"}, False)), \
                patch.object(policy, "call", side_effect=transport) as call, patch.object(policy, "audit"):
            with self.assertRaisesRegex(RuntimeError, "options"):
                policy.delegate({"task": "Inspect issue", "title": "[sub] [routing] inspect issue", "clientRequestId": "r1"})
            self.assertEqual(call.call_args.args[0], "task_cancel")


class RelayBoundaryTest(unittest.TestCase):
    def test_child_questions_and_followups_refused_but_host_security_decision_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            bridge = home / "bridge"
            bridge.write_text("#!" + sys.executable + "\nimport json,sys\n"
                              "tool=sys.argv[-2]\n"
                              "data={'parentThreadId':'child'} if tool=='orchestrator_capabilities' else "
                              "{'thread':{'threadId':'child','parentThreadId':'parent','relationshipToParent':'subagent','runCount':1}}\n"
                              "print(json.dumps({'content':[{'text':json.dumps(data)}]}))\n")
            bridge.chmod(0o755)
            agent = home / "agent"
            agent.write_text("#!" + sys.executable + "\nimport json,sys\nfrom pathlib import Path\n"
                             "for line in sys.stdin:\n"
                             " m=json.loads(line)\n"
                             " with (Path.home()/'received.jsonl').open('a') as f:f.write(json.dumps(m)+'\\n')\n"
                             " if m.get('method')=='session/prompt':\n"
                             "  for i,method in ((100,'elicitation/create'),(101,'session/request_permission')):\n"
                             "   print(json.dumps({'jsonrpc':'2.0','id':i,'method':method,'params':{'sessionId':'s'}}),flush=True)\n"
                             " if m.get('id')==101 and 'result' in m:\n"
                             "  print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'stopReason':'end_turn'}}),flush=True)\n")
            agent.chmod(0o755)
            relay = Path(__file__).with_name("omp_acp.py")
            environment = {**os.environ, "HOME": str(home), "FEEDBACK_OMP_BIN": str(agent),
                           "FEEDBACK_DISABLED": "1", "T3_ACP_MCP_NODE": str(bridge)}
            environment.pop("T3_ACP_MCP_ENTRYPOINT", None)
            process = subprocess.Popen([sys.executable, str(relay), "acp"], env=environment,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            prompt = {"jsonrpc": "2.0", "id": 1, "method": "session/prompt", "params": {
                "sessionId": "s", "prompt": [{"type": "text", "text": "bounded task"}]}}
            process.stdin.write(json.dumps(prompt) + "\n")
            process.stdin.flush()
            seen = []
            while True:
                message = json.loads(process.stdout.readline())
                seen.append(message)
                if message.get("method") == "session/request_permission":
                    # Only the host decides permission; the relay must not fabricate acceptance.
                    process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 101,
                                        "result": {"outcome": {"outcome": "cancelled"}}}) + "\n")
                    process.stdin.flush()
                if message.get("id") == 1:
                    break
            prompt["id"] = 2
            process.stdin.write(json.dumps(prompt) + "\n")
            process.stdin.flush()
            rejected = json.loads(process.stdout.readline())
            self.assertIn("Child input disabled", rejected["error"]["message"])
            process.stdin.close()
            process.wait(timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr.read())
            received = [json.loads(line) for line in (home / "received.jsonl").read_text().splitlines()]
            self.assertEqual(sum(m.get("method") == "session/prompt" for m in received), 1)
            replies = {m["id"]: m["result"] for m in received if "result" in m}
            self.assertEqual(replies[100], {"action": "cancel"})
            self.assertEqual(replies[101], {"outcome": {"outcome": "cancelled"}})
            self.assertFalse(any(m.get("method") == "elicitation/create" for m in seen))
            self.assertTrue(any(m.get("method") == "session/request_permission" for m in seen))
            process.stdout.close()
            process.stderr.close()


def subagent_update(status, tool=None, started=None, tool_count=0):
    progress = {"id": "Judge", "agent": "easy-haiku", "status": status, "description": "blind A/B judge",
                "currentTool": tool, "currentToolStartMs": started, "toolCount": tool_count, "durationMs": 0}
    return {"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": "s", "update": {
        "sessionUpdate": "tool_call_update", "toolCallId": "call", "rawOutput": {"details": {"progress": [progress]}}}}}


class SubagentBoardTest(unittest.TestCase):
    def setUp(self):
        import omp_acp
        self.now = 1_790_000_000.0
        self.board = omp_acp.SubagentBoard(clock=lambda: self.now)
        todo = {"content": "Unblind, report", "priority": "medium", "status": "pending"}
        self.board.observe({"jsonrpc": "2.0", "method": "session/update", "params": {
            "sessionId": "s", "update": {"sessionUpdate": "plan", "entries": [todo]}}})

    def entries(self, plan):
        return plan["params"]["update"]["entries"]

    def test_subagent_rows_follow_todos_and_flag_silence(self):
        plan = self.board.observe(subagent_update("running", "bash", self.now * 1000, 3))
        todo, row = self.entries(plan)
        self.assertEqual(todo["content"], "Unblind, report")
        self.assertEqual(row["status"], "in_progress")
        self.assertEqual(row["content"], "⑂ Judge (easy-haiku): blind A/B judge — bash <1m · 3 tools · <1m")
        self.now += 30
        self.assertEqual(self.board.tick(), [], "sub-minute drift must not re-send the plan")
        self.now += 150
        row = self.entries(self.board.tick()[0])[1]
        # durationMs stays 0 in the update; elapsed must still advance with wall time.
        self.assertTrue(row["content"].endswith("bash 3m · ⚠ quiet 3m · 3 tools · 3m"), row["content"])
        stale = self.entries(self.board.observe(subagent_update("pending")))[1]
        self.assertEqual(stale["status"], "in_progress", "late spawn snapshot must not demote a running row")

    def test_replayed_history_adds_no_ghost_rows(self):
        self.board.replaying.add("s")
        self.assertIsNone(self.board.observe(subagent_update("pending")))
        self.board.replaying.discard("s")
        self.assertEqual(len(self.entries(self.board.plan("s", force=True))), 1)

    def test_event_bus_keeps_background_rows_current_after_the_turn(self):
        self.board.observe(subagent_update("pending"))  # spawn snapshot: the last ACP progress for this agent
        self.assertIsNone(self.board.feed({"kind": "progress", "parentToolCallId": "elsewhere",
                                           "progress": {"id": "Judge", "status": "running"}}))
        plan = self.board.feed({"kind": "progress", "parentToolCallId": "call", "progress": {
            "id": "Judge", "agent": "easy-haiku", "status": "running", "currentTool": "bash", "toolCount": 4}})
        self.assertIn("bash · 4 tools", self.entries(plan)[1]["content"])
        # Once the bus owns a row, stale ACP snapshots no longer overwrite it.
        self.assertIsNone(self.board.observe(subagent_update("pending")))
        done = self.board.feed({"kind": "lifecycle", "parentToolCallId": "call", "id": "Judge", "status": "completed"})
        self.assertEqual(self.entries(done)[1]["status"], "completed")
        self.assertEqual(self.board.tick(), [])
        self.assertIsNone(self.board.feed({"kind": "progress", "parentToolCallId": "call",
                                           "progress": {"id": "Judge", "status": "running"}}))

    def test_new_prompt_drops_finished_subagents_only(self):
        self.board.observe(subagent_update("completed", tool_count=5))
        self.assertEqual(self.entries(self.board.plan("s", force=True))[1]["status"], "completed")
        self.board.settle("s")
        self.assertEqual(len(self.entries(self.board.plan("s", force=True))), 1)
        self.board.observe(subagent_update("running"))
        self.board.settle("s")
        self.assertEqual(len(self.entries(self.board.plan("s", force=True))), 2)
        self.assertIsNone(self.board.observe({"method": "session/update", "params": {"sessionId": "s", "update": {
            "sessionUpdate": "tool_call_update", "toolCallId": "other", "rawOutput": {"content": []}}}}))


if __name__ == "__main__":
    unittest.main()
