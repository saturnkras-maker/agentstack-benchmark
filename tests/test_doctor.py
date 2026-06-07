from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.cli import main
from agentstack_benchmark.doctor import build_first_run_doctor_report


class FirstRunDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-doctor-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_doctor_report_is_local_safe_and_actionable(self) -> None:
        report = build_first_run_doctor_report(
            repo_root=self.tmpdir,
            host="127.0.0.1",
            ui_port=8095,
            agent_port=8769,
            probe_local_model=False,
        )

        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["internetRequired"], False)
        self.assertEqual(report["apiKeysRequired"], False)
        self.assertEqual(report["recommendedMode"], "offline")
        self.assertIn("demo-local", report["commands"]["offlineDemo"])
        self.assertIn("--agent-mode auto-local-model", report["commands"]["autoLocalModel"])
        self.assertEqual(report["urls"]["runForm"], "http://127.0.0.1:8095/run")
        self.assertEqual(report["urls"]["agentEndpoint"], "http://127.0.0.1:8769/tasks")
        self.assertEqual(report["localModel"]["available"], False)
        self.assertEqual(report["localModel"]["reason"], "probe-skipped")
        self.assertNotIn("token", json.dumps(report).lower())
        self.assertNotIn("secret", json.dumps(report).lower())

    def test_doctor_cli_prints_json_without_starting_servers(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "doctor",
                    "--host",
                    "127.0.0.1",
                    "--ui-port",
                    "8095",
                    "--agent-port",
                    "8769",
                    "--skip-local-model-probe",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["urls"]["ui"], "http://127.0.0.1:8095/")
        self.assertIn("local-model-check", payload["commands"]["localModelCheck"])
        self.assertEqual(payload["doesNotStartServers"], True)


if __name__ == "__main__":
    unittest.main()
