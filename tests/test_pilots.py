from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.leaderboard import collect_leaderboard_rows
from agentstack_benchmark.runner import run_benchmark

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PILOT_IDS = [
    "openai-agents-sdk",
    "langgraph",
    "autogen",
    "crewai",
    "claude-mcp",
]


class PilotRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-pilots-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_local_public_pilot_registry_selects_five_credible_frameworks(self) -> None:
        from agentstack_benchmark.pilots import load_pilot_registry

        registry = load_pilot_registry(PROJECT_ROOT / "examples/pilots/local_public_v0_1.json")

        self.assertEqual(registry["schemaVersion"], "agentstack-benchmark.pilot-registry.v0.1")
        self.assertEqual(registry["track"], "local-public")
        self.assertEqual(registry["taskPackPath"], "examples/task_packs/beta_v0_1.json")
        self.assertTrue(registry["localOnly"])
        self.assertEqual([pilot["pilotId"] for pilot in registry["pilots"]], EXPECTED_PILOT_IDS)

        for pilot in registry["pilots"]:
            self.assertEqual(pilot["track"], "local-public")
            self.assertEqual(pilot["localPilotMode"], "fixture-adapter")
            self.assertFalse(pilot["requiresPrivateKeys"])
            self.assertTrue(pilot["manifestPath"].startswith("examples/manifests/pilots/"))
            self.assertGreaterEqual(len(pilot["sourceUrls"]), 1)
            self.assertTrue(all(url.startswith("https://") for url in pilot["sourceUrls"]))
            self.assertGreaterEqual(len(pilot["selectionRationale"]), 40)
            self.assertGreaterEqual(len(pilot["coverage"]), 2)
            self.assertIn("not executed", pilot["realExecutionBoundary"])

    def test_five_local_pilot_manifests_are_runnable_and_rankable(self) -> None:
        from agentstack_benchmark.pilots import load_pilot_registry, run_local_pilots

        registry_path = PROJECT_ROOT / "examples/pilots/local_public_v0_1.json"
        registry = load_pilot_registry(registry_path)
        reports = run_local_pilots(
            registry_path,
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "runs",
        )

        self.assertEqual(len(reports), 5)
        self.assertEqual([report["pilotId"] for report in reports], EXPECTED_PILOT_IDS)
        for run in reports:
            report = run["report"]
            pilot = next(item for item in registry["pilots"] if item["pilotId"] == run["pilotId"])
            self.assertEqual(report["track"], "local-public")
            self.assertEqual(report["agent"]["agentId"], pilot["agentId"])
            self.assertGreaterEqual(report["summary"]["overall"], 95.0)
            self.assertEqual(report["taskPack"]["taskPackId"], "agentstack-mvp-v0")
            self.assertTrue((self.tmpdir / "runs" / pilot["pilotId"] / "report.json").exists())

        rows = collect_leaderboard_rows(self.tmpdir / "runs")
        self.assertEqual(len(rows), 5)
        self.assertEqual({row["track"] for row in rows}, {"local-public"})
        self.assertEqual({row["tasksTotal"] for row in rows}, {5})

    def test_pilot_run_cli_generates_reports_and_leaderboard(self) -> None:
        from agentstack_benchmark.cli import main

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "pilot-run",
                    "--registry",
                    str(PROJECT_ROOT / "examples/pilots/local_public_v0_1.json"),
                    "--task-pack",
                    str(PROJECT_ROOT / "examples/task_packs/mvp_v0.json"),
                    "--out-dir",
                    str(self.tmpdir / "cli-runs"),
                    "--leaderboard-out",
                    str(self.tmpdir / "pilot-leaderboard.json"),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["pilots"], 5)
        self.assertTrue((self.tmpdir / "pilot-leaderboard.json").exists())
        leaderboard = json.loads((self.tmpdir / "pilot-leaderboard.json").read_text())
        self.assertEqual(len(leaderboard), 5)
        self.assertEqual({row["track"] for row in leaderboard}, {"local-public"})


if __name__ == "__main__":
    unittest.main()
