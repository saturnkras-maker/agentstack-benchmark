from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class LocalMVPVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-verify-local-mvp-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_verify_local_mvp_runs_demo_and_checks_browser_surfaces(self) -> None:
        from agentstack_benchmark.local_mvp_verification import verify_local_mvp

        report = verify_local_mvp(
            repo_root=REPO_ROOT,
            out_dir=self.tmpdir,
            host="127.0.0.1",
            ui_port=0,
            agent_port=0,
            run_id="verification-demo-run",
        )

        self.assertEqual(report["schemaVersion"], "agentstack-benchmark.local-mvp-verification.v0.1")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["run"]["runId"], "verification-demo-run")
        self.assertEqual(report["run"]["overall"], 98.88)
        self.assertEqual(report["run"]["tasksPassed"], 5)
        self.assertEqual(report["run"]["tasksTotal"], 5)
        self.assertFalse(report["internetRequired"])
        self.assertFalse(report["apiKeysRequired"])
        self.assertFalse(report["billingCheckoutConnected"])
        checked_paths = {endpoint["path"] for endpoint in report["endpointChecks"]}
        self.assertTrue(
            {
                "/api/v1/healthz",
                "/cockpit",
                "/api/v1/cockpit",
                "/run",
                "/leaderboard",
                "/runs/verification-demo-run",
            }.issubset(checked_paths)
        )
        self.assertTrue(all(endpoint["ok"] for endpoint in report["endpointChecks"]))
        self.assertTrue((self.tmpdir / "local_mvp_verification.json").exists())
        self.assertTrue((self.tmpdir / "local_mvp_verification.md").exists())
        self.assertIn("PASS", (self.tmpdir / "local_mvp_verification.md").read_text())

    def test_verify_local_mvp_cli_writes_proof_summary(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = cli_main(
                [
                    "verify-local-mvp",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--out-dir",
                    str(self.tmpdir),
                    "--ui-port",
                    "0",
                    "--agent-port",
                    "0",
                    "--run-id",
                    "cli-verification-demo-run",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["overall"], 98.88)
        self.assertEqual(payload["tasks"], "5/5")
        self.assertEqual(payload["endpointsChecked"], 6)
        self.assertEqual(payload["outDir"], str(self.tmpdir))
        self.assertTrue((self.tmpdir / "local_mvp_verification.json").exists())


if __name__ == "__main__":
    unittest.main()
