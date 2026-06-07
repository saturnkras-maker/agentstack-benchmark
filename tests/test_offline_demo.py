from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.cli import build_parser, main
from agentstack_benchmark.offline_demo import run_offline_demo_once, write_offline_demo_manifest
from agentstack_benchmark.runner import run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OfflineDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-offline-demo-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_offline_demo_manifest_runs_mvp_pack_without_internet_or_api_keys(self) -> None:
        summary = run_offline_demo_once(
            runs_dir=self.tmpdir / "runs",
            run_id="offline-demo-unit",
            host="127.0.0.1",
            agent_port=0,
        )

        report_path = self.tmpdir / "runs/offline-demo-unit/report.json"
        self.assertTrue(report_path.exists())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["agent"]["agentId"], "offline-demo-agent")
        self.assertEqual(report["track"], "local-public")
        self.assertGreater(report["summary"]["overall"], 90)
        self.assertEqual(report["summary"]["tasksPassed"], 5)
        self.assertEqual(summary["internetRequired"], False)
        self.assertEqual(summary["apiKeysRequired"], False)
        self.assertEqual(summary["reportUrl"], "/runs/offline-demo-unit")
        serialized_summary = json.dumps(summary, ensure_ascii=False)
        self.assertNotIn("sk_live_", serialized_summary)
        self.assertNotIn("Bearer ", serialized_summary)
        self.assertNotIn("password=", serialized_summary)

    def test_offline_demo_manifest_helper_writes_loopback_http_manifest(self) -> None:
        manifest_path = self.tmpdir / "offline_demo.json"

        manifest = write_offline_demo_manifest(
            "http://127.0.0.1:8765/tasks",
            manifest_path,
        )

        persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["agentId"], "offline-demo-agent")
        self.assertEqual(persisted["adapter"]["type"], "http")
        self.assertEqual(persisted["adapter"]["endpoint"], "http://127.0.0.1:8765/tasks")
        self.assertEqual(persisted["limits"]["maxRunsPerTask"], 1)

    def test_demo_local_cli_once_prints_touchable_local_urls(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(
                [
                    "demo-local",
                    "--once",
                    "--agent-port",
                    "0",
                    "--ui-port",
                    "8099",
                    "--runs-dir",
                    str(self.tmpdir / "runs"),
                    "--run-id",
                    "cli-offline-demo",
                ]
            )

        self.assertEqual(code, 0)
        body = json.loads(stdout.getvalue())
        self.assertEqual(body["mode"], "offline-local-demo")
        self.assertEqual(body["internetRequired"], False)
        self.assertEqual(body["apiKeysRequired"], False)
        self.assertEqual(body["runId"], "cli-offline-demo")
        self.assertEqual(body["uiUrl"], "http://127.0.0.1:8099/")
        self.assertEqual(body["runFormUrl"], "http://127.0.0.1:8099/run")
        self.assertEqual(body["reportUrl"], "http://127.0.0.1:8099/runs/cli-offline-demo")
        self.assertGreater(body["overall"], 90)

    def test_cli_help_exposes_demo_local_command(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("demo-local", help_text)
        self.assertIn("offline", help_text.lower())


if __name__ == "__main__":
    unittest.main()
