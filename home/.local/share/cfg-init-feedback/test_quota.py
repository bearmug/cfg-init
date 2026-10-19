"""Quota snapshot, recommendation and delegation gate; fixture-driven, never runs real `omp`."""
import copy
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

os.environ["T3_QUOTA"] = "off"  # Real gate stays off unless a test turns it on.
import quota  # noqa: E402
import t3_policy as policy  # noqa: E402

FIXTURE = json.loads((Path(__file__).with_name("testdata") / "omp-usage.json").read_text())
NOW = FIXTURE["generatedAt"] / 1000 + 120  # reading is two minutes old
CONFIG = dict(quota.settings(), buffer=0.15, margin=0.15, stale=1800, ttl=600, ttl_tight=180, retry=120)


def usage(**changes):
    """Fixture copy; changes map `provider:window` to remainingFraction or a dict of overrides."""
    report = copy.deepcopy(FIXTURE)
    for key, value in changes.items():
        provider, window = key.replace("_", "-").split(":")
        value = value if isinstance(value, dict) else {"remaining": value}
        for item in report["reports"]:
            for limit in item["limits"] if item["provider"] == provider else []:
                if limit["window"]["id"] == window:
                    if "remaining" in value:
                        limit["amount"]["remainingFraction"] = value["remaining"]
                        limit["amount"]["usedFraction"] = 1 - value["remaining"]
                    limit["status"] = value.get("status", limit["status"])
                    limit["window"]["resetsAt"] = value.get("resetsAt", limit["window"]["resetsAt"])
        for row in report["capacity"].get(provider, []):
            if row["window"] == window and "remaining" in value:
                row["remainingAccounts"] = value["remaining"] * row["accounts"]
    return report


def snap(report=None, taken=NOW):
    return {"takenAt": taken, "providers": quota.summarize(report or FIXTURE)}


class RecommendationTest(unittest.TestCase):
    def advice(self, provider, report=None, now=NOW):
        return quota.assess(provider, snap(report), CONFIG, now)

    def test_summary_drops_account_metadata_and_credit_ids(self):
        text = json.dumps(quota.summarize(FIXTURE))
        for secret in ("redacted-email", "redacted-id", "redacted-org", "redacted-credit", "example.invalid", "plan"):
            self.assertNotIn(secret, text)
        self.assertEqual(quota.summarize(FIXTURE)["anthropic"]["resetCredits"], 1)

    def test_healthy_reading_is_ok_with_age_from_omp_fetch_time(self):
        for provider in ("openai-codex", "anthropic"):
            advice = self.advice(provider)
            self.assertEqual(advice["recommendation"], "ok", advice)
            self.assertEqual(advice["ageSec"], 120)
        self.assertEqual(self.advice("anthropic")["window"], "5h")  # tightest window is reported

    def test_reserve_and_reduce_band(self):
        self.assertEqual(self.advice("anthropic", usage(**{"anthropic:5h": 0.25}))["recommendation"], "reduce")
        avoid = self.advice("anthropic", usage(**{"anthropic:5h": 0.12}))
        self.assertEqual((avoid["recommendation"], avoid["window"]), ("avoid", "5h"))
        self.assertEqual(self.advice("openai-codex", usage(**{"openai-codex:7d": 0.15}))["recommendation"], "avoid")

    def test_exhausted_status_and_limit_reached_avoid(self):
        report = usage(**{"anthropic:7d": {"status": "exhausted"}})
        self.assertEqual(self.advice("anthropic", report)["recommendation"], "avoid")
        report = copy.deepcopy(FIXTURE)
        report["reports"][0]["metadata"]["limitReached"] = True
        advice = self.advice("openai-codex", report)
        self.assertEqual((advice["recommendation"], advice.get("limitReached")), ("avoid", True))

    def test_window_that_already_reset_is_ignored(self):
        past = int((NOW - 60) * 1000)
        report = usage(**{"anthropic:5h": {"remaining": 0.02, "resetsAt": past}})
        advice = self.advice("anthropic", report)
        self.assertEqual((advice["recommendation"], advice["window"]), ("ok", "7d"))

    def test_pace_only_raises_reduce_and_not_early_in_window(self):
        # 7d window 57% elapsed, 55% used -> projected 96% > 85%: reduce, not avoid.
        self.assertEqual(self.advice("openai-codex", usage(**{"openai-codex:7d": 0.45}))["recommendation"], "reduce")
        early = int((NOW + 0.95 * 604800) * 1000)  # 5% elapsed: too early to project
        report = usage(**{"openai-codex:7d": {"remaining": 0.6, "resetsAt": early}})
        self.assertEqual(self.advice("openai-codex", report)["recommendation"], "ok")
        self.assertEqual(self.advice("anthropic", usage(**{"anthropic:7d": {"status": "warning"}}))["recommendation"],
                         "reduce")

    def test_stale_reading_is_unknown_but_keeps_last_values(self):
        advice = self.advice("anthropic", usage(**{"anthropic:5h": 0.05}), now=NOW + 3600)
        self.assertEqual((advice["recommendation"], advice["last"]), ("unknown", "avoid"))
        self.assertIn("stale", advice["why"])

    def test_pool_capacity_beats_single_exhausted_account(self):
        report = copy.deepcopy(FIXTURE)
        second = copy.deepcopy(report["reports"][0])
        second["limits"][0]["amount"]["remainingFraction"] = 0.05
        report["reports"].insert(1, second)
        report["capacity"]["openai-codex"][0].update(accounts=2, remainingAccounts=0.65)
        advice = self.advice("openai-codex", report)
        self.assertEqual(advice["recommendation"], "reduce")  # pool 32.5% left: near reserve, not exhausted
        self.assertAlmostEqual(advice["remaining"], 0.325, places=3)

    def test_window_without_capacity_row_still_counts(self):
        report = usage(**{"anthropic:7d": 0.05})
        report["capacity"]["anthropic"] = [row for row in report["capacity"]["anthropic"] if row["window"] == "5h"]
        advice = self.advice("anthropic", report)
        self.assertEqual((advice["recommendation"], advice["window"]), ("avoid", "7d"))

    def test_staggered_reset_skips_outdated_pool_window(self):
        report = copy.deepcopy(FIXTURE)
        second = copy.deepcopy(report["reports"][0])
        second["limits"][0]["window"]["resetsAt"] = int((NOW - 60) * 1000)  # this account reset already
        report["reports"][0]["limits"][0]["status"] = "exhausted"
        report["reports"].append(second)
        report["capacity"]["openai-codex"][0].update(accounts=2, remainingAccounts=0.3)
        self.assertEqual(self.advice("openai-codex", report)["recommendation"], "unknown")  # no live window

    def test_undated_reading_is_unknown(self):
        report = copy.deepcopy(FIXTURE)
        del report["reports"][1]["fetchedAt"]
        advice = self.advice("anthropic", report)
        self.assertEqual((advice["recommendation"], advice["why"]), ("unknown", "reading has no fetch time"))

    def test_missing_provider_and_unprefixed_model_are_unknown(self):
        self.assertEqual(self.advice("google")["recommendation"], "unknown")
        self.assertEqual(quota.assess(None, snap(), CONFIG, NOW)["recommendation"], "unknown")
        self.assertEqual(quota.assess("anthropic", None, CONFIG, NOW)["recommendation"], "unknown")

    def test_siblings_are_same_tier_other_provider(self):
        self.assertEqual(quota.siblings("high-opus", policy.TIERS), ["high-sol"])
        self.assertEqual(quota.siblings("easy-luna", policy.TIERS), ["easy-haiku"])
        self.assertEqual(quota.siblings("mid-sonnet", policy.TIERS), [])


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"XDG_STATE_HOME": self.directory.name, "T3_OMP_BIN": "/bin/omp-test"})
        self.env.start()
        self.path = Path(self.directory.name) / "cfg-init-t3" / "quota.json"

    def tearDown(self):
        self.env.stop()
        self.directory.cleanup()

    def run_omp(self, stdout="", code=0):
        return subprocess.CompletedProcess(["omp"], code, stdout=stdout, stderr="")

    def test_refresh_caches_private_summary_and_reuses_within_ttl(self):
        with patch.object(quota.subprocess, "run", return_value=self.run_omp(json.dumps(FIXTURE))) as run:
            first = quota.snapshot(CONFIG, now=NOW)
            second = quota.snapshot(CONFIG, now=NOW + 300)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["/bin/omp-test", "usage", "--json", "--redact"])
        self.assertEqual(first, second)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertNotIn("redacted", self.path.read_text())

    def test_tight_quota_refreshes_sooner(self):
        tight = json.dumps(usage(**{"anthropic:5h": 0.25}))
        with patch.object(quota.subprocess, "run", return_value=self.run_omp(tight)) as run:
            quota.snapshot(CONFIG, now=NOW)
            quota.snapshot(CONFIG, now=NOW + 200)  # > ttl_tight, < ttl
        self.assertEqual(run.call_count, 2)

    def test_garbage_failure_and_missing_omp_are_unknown_with_backoff(self):
        for outcome in (self.run_omp("not json"), self.run_omp("", code=2), FileNotFoundError("omp")):
            with self.subTest(outcome=outcome):
                if self.path.exists():
                    self.path.unlink()
                with patch.object(quota.subprocess, "run", side_effect=[outcome]) as run:
                    result = quota.snapshot(CONFIG, now=NOW)
                    quota.snapshot(CONFIG, now=NOW + 60)  # within retry back-off: no second call
                self.assertEqual(run.call_count, 1)
                self.assertIn("error", result)
                self.assertEqual(quota.assess("anthropic", result, CONFIG, NOW)["recommendation"], "unknown")

    def test_failed_refresh_keeps_last_reading(self):
        with patch.object(quota.subprocess, "run", return_value=self.run_omp(json.dumps(FIXTURE))):
            quota.snapshot(CONFIG, now=NOW)
        with patch.object(quota.subprocess, "run", side_effect=subprocess.TimeoutExpired("omp", 8)):
            kept = quota.snapshot(CONFIG, refresh=True, now=NOW + 10)
        self.assertEqual(kept["error"], "TimeoutExpired")
        self.assertEqual(quota.assess("anthropic", kept, CONFIG, NOW + 10)["recommendation"], "ok")

    def test_corrupt_cache_is_refreshed(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"takenAt": "yesterday", "providers": []}))
        with patch.object(quota.subprocess, "run", return_value=self.run_omp(json.dumps(FIXTURE))) as run:
            result = quota.snapshot(CONFIG, now=NOW)
        run.assert_called_once()
        self.assertIn("anthropic", result["providers"])

    def test_check_lines_are_cached_only(self):
        with patch.object(quota.subprocess, "run") as run:
            self.assertEqual(quota.check_lines(CONFIG, NOW), ["ok quota: no snapshot yet (quota.py --refresh)"])
            self.path.parent.mkdir(parents=True)
            self.path.write_text(json.dumps(snap(usage(**{"anthropic:5h": 0.1}))))
            lines = quota.check_lines(CONFIG, NOW)
        run.assert_not_called()
        self.assertTrue(lines[0].startswith("warn quota: anthropic, avoid, 5h 10% left"), lines)
        self.assertTrue(lines[1].startswith("ok quota: openai-codex, ok"), lines)


class GateTest(unittest.TestCase):
    def gate(self, report, lane="high-opus", override=None, mode="enforce"):
        with patch.dict(os.environ, {"T3_QUOTA": mode}), patch.object(quota, "snapshot", return_value=snap(report)):
            return quota.gate(lane, policy.TIERS.get(lane, "anthropic/pinned-model"), policy.TIERS, override, now=NOW)

    def test_avoid_refuses_and_names_sibling_without_switching(self):
        with self.assertRaises(quota.QuotaAvoid) as caught:
            self.gate(usage(**{"anthropic:5h": 0.1}))
        message = str(caught.exception)
        self.assertIn("high-sol", message)
        self.assertIn("5h 10% left", message)
        self.assertIn("saved usage reset", message)
        self.assertEqual(caught.exception.advice["recommendation"], "avoid")

    def test_no_sibling_headroom_asks_user(self):
        report = usage(**{"anthropic:5h": 0.1, "openai-codex:7d": 0.05})
        with self.assertRaisesRegex(quota.QuotaAvoid, "ask the user"):
            self.gate(report)
        with self.assertRaisesRegex(quota.QuotaAvoid, "ask the user"):
            self.gate(usage(**{"anthropic:5h": 0.1}), lane="mid-sonnet")

    def test_override_pin_advise_and_off_do_not_block(self):
        low = usage(**{"anthropic:5h": 0.1})
        self.assertEqual(self.gate(low, override="user approved spending reserve")["override"],
                         "user approved spending reserve")
        self.assertEqual(self.gate(low, lane="pinned")["recommendation"], "avoid")
        self.assertEqual(self.gate(low, mode="advise")["recommendation"], "avoid")
        self.assertEqual(self.gate(low, mode="off"), {"recommendation": "off"})
        self.assertEqual(self.gate(usage(**{"anthropic:5h": 0.25}))["recommendation"], "reduce")

    def test_override_cannot_spend_a_reached_limit(self):
        report = copy.deepcopy(FIXTURE)
        report["reports"][1]["metadata"]["limitReached"] = True
        with self.assertRaisesRegex(quota.QuotaAvoid, "override would fail"):
            self.gate(report, override="user approved")

    def test_malformed_sibling_data_never_crashes(self):
        broken = snap(usage(**{"anthropic:5h": 0.1}))
        broken["providers"]["openai-codex"]["fetchedAt"] = "bad"
        broken["providers"]["openai-codex"]["limits"][0]["remaining"] = "bad"
        with patch.dict(os.environ, {"T3_QUOTA": "enforce"}), patch.object(quota, "snapshot", return_value=broken):
            with self.assertRaisesRegex(quota.QuotaAvoid, "high-sol \\(openai-codex, unknown"):
                quota.gate("high-opus", policy.TIERS["high-opus"], policy.TIERS, now=NOW)
            broken["providers"]["anthropic"]["limits"] = "garbage"
            self.assertEqual(quota.gate("high-opus", policy.TIERS["high-opus"], policy.TIERS, now=NOW)["recommendation"],
                             "unknown")

    def test_snapshot_crash_never_blocks(self):
        with patch.dict(os.environ, {"T3_QUOTA": "enforce"}), \
                patch.object(quota, "snapshot", side_effect=RuntimeError("boom")):
            self.assertEqual(quota.gate("high-sol", policy.TIERS["high-sol"], policy.TIERS)["recommendation"], "unknown")


def catalog():
    options = [{"id": "thinking", "type": "select", "options": [{"id": "auto"}]},
               {"id": "mode", "type": "select", "options": [{"id": "default"}]}]
    return {"parentThreadId": "parent", "providers": [{"providerInstanceId": "omp", "canRunChildTask": True,
            "models": [{"id": m, "options": options} for m in policy.TIERS.values()]}]}


class DelegateIntegrationTest(unittest.TestCase):
    assignment = {"task": "Inspect bounded issue", "title": "[sub] [routing] inspect issue",
                  "clientRequestId": "q1"}

    def delegate(self, report, **request):
        audits = []
        calls = []

        def transport(tool, args):
            calls.append(tool)
            model = args.get("target", {}).get("model", policy.TIERS[policy.DEFAULT_LANE])
            if tool == "delegate_task":
                transport.model = model
                return {"taskId": "task", "childThreadId": "child", "providerInstanceId": "omp", "model": model}
            if tool == "t3_thread_configuration":
                return {"modelSelection": {"instanceId": "omp", "model": transport.model,
                                           "options": {"thinking": "auto", "mode": "default"}}}
            return {}
        with patch.dict(os.environ, {"T3_QUOTA": "enforce"}), \
                patch.object(quota, "snapshot", return_value=snap(report)), \
                patch.object(quota.time, "time", return_value=NOW), \
                patch.object(policy, "context", return_value=(catalog(), {"threadId": "parent"}, False)), \
                patch.object(policy, "call", side_effect=transport), \
                patch.object(policy, "audit", side_effect=audits.append):
            try:
                return policy.delegate({**self.assignment, **request}), audits, calls
            except quota.QuotaAvoid as error:
                return error, audits, calls

    def test_refusal_is_audited_and_launches_nothing(self):
        error, audits, calls = self.delegate(usage(**{"openai-codex:7d": 0.1}))  # default lane high-sol
        self.assertIsInstance(error, quota.QuotaAvoid)
        self.assertIn("high-opus", str(error))
        self.assertEqual(calls, [])
        self.assertEqual([a["status"] for a in audits], ["refused-quota"])
        self.assertEqual(audits[0]["quota"]["window"], "7d")

    def test_reduce_launches_and_surfaces_advice(self):
        result, audits, calls = self.delegate(usage(**{"anthropic:5h": 0.25}), lane="high-opus", reason="hard review")
        self.assertIn("delegate_task", calls)
        self.assertEqual(result["quota"]["recommendation"], "reduce")
        self.assertEqual([a["status"] for a in audits], ["requested", "launched"])
        self.assertTrue(all(a["quota"]["recommendation"] == "reduce" for a in audits))


if __name__ == "__main__":
    unittest.main()
