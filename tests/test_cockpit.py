from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.cockpit import build_local_mvp_cockpit_report
from agentstack_benchmark.runner import run_benchmark


REPO_ROOT = Path(__file__).resolve().parents[1]


class LocalMVPCockpitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-cockpit-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cockpit_report_is_local_safe_actionable_and_ranked(self) -> None:
        task_pack = REPO_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(REPO_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(REPO_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")

        report = build_local_mvp_cockpit_report(
            runs_dir=self.tmpdir / "runs",
            repo_root=REPO_ROOT,
            host="127.0.0.1",
            ui_port=8099,
            agent_port=8773,
            probe_local_model=False,
        )

        self.assertEqual(report["schemaVersion"], "agentstack-benchmark.local-mvp-cockpit.v0.1")
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["track"], "local-public")
        self.assertEqual(report["internetRequired"], False)
        self.assertEqual(report["apiKeysRequired"], False)
        self.assertEqual(report["billingCheckoutConnected"], False)
        self.assertEqual(report["hostedVerifiedStatus"], "reserved")
        self.assertEqual(report["recommendedNextAction"], "run-offline-demo")
        self.assertEqual(report["doctor"]["doesNotStartServers"], True)
        self.assertEqual(report["urls"]["cockpit"], "http://127.0.0.1:8099/cockpit")
        self.assertEqual(report["urls"]["runForm"], "http://127.0.0.1:8099/run")
        self.assertIn("make doctor", report["commands"]["doctor"])
        self.assertIn("make demo-local", report["commands"]["offlineDemo"])
        self.assertIn("make demo-local-auto", report["commands"]["autoLocalModel"])
        self.assertEqual(report["runs"]["count"], 2)
        self.assertEqual(report["runs"]["leader"]["agentId"], "mock-good-agent")
        self.assertIn("docs/local-mvp-cockpit-v0.1.md", report["docs"])
        serialized = json.dumps(report)
        self.assertNotIn(str(self.tmpdir), serialized)
        self.assertNotIn("token", serialized.lower())
        self.assertNotIn("secret", serialized.lower())


if __name__ == "__main__":
    unittest.main()
