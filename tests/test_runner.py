from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.leaderboard import build_leaderboard
from agentstack_benchmark.runner import run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-benchmark-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_good_agent_scores_higher_than_bad_agent(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        good = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            task_pack,
            self.tmpdir / "good",
        )
        bad = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_bad.json",
            task_pack,
            self.tmpdir / "bad",
        )

        self.assertGreater(good["summary"]["overall"], 90)
        self.assertLess(bad["summary"]["overall"], 25)
        self.assertGreater(good["summary"]["overall"], bad["summary"]["overall"])
        self.assertTrue((self.tmpdir / "good/report.json").exists())
        self.assertTrue((self.tmpdir / "good/report.md").exists())

    def test_report_contains_manifest_and_task_pack_hashes(self) -> None:
        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )
        self.assertEqual(len(report["agent"]["manifestHash"]), 64)
        self.assertEqual(len(report["taskPack"]["taskPackHash"]), 64)

    def test_leaderboard_ranks_good_agent_first(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")

        rows = build_leaderboard(self.tmpdir / "runs", self.tmpdir / "leaderboard.json")

        self.assertEqual(rows[0]["agentId"], "mock-good-agent")
        self.assertEqual(rows[0]["rank"], 1)
        self.assertTrue((self.tmpdir / "leaderboard.json").exists())
        self.assertTrue((self.tmpdir / "leaderboard.md").exists())


if __name__ == "__main__":
    unittest.main()
