from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.public_demo import build_public_demo_site


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicDemoSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-public-demo-site-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_public_demo_generator_writes_static_sample_report_and_leaderboard(self) -> None:
        manifest = build_public_demo_site(REPO_ROOT, self.tmpdir)

        self.assertEqual(manifest["schemaVersion"], "agentstack-benchmark.public-demo.v0.1")
        self.assertEqual(manifest["status"], "static-local-public-sample-ready")
        self.assertEqual(manifest["sampleRun"]["agentName"], "Offline Demo Agent")
        self.assertEqual(manifest["sampleRun"]["overall"], 98.88)
        # Public leaderboard now reflects the honest engine's real frontier run
        # (Opus > Sonnet > Haiku + a handicapped-weak control), not the old
        # deterministic 5-pilot fixture that flattened every stack to a near-tie.
        self.assertEqual(manifest["pilotLeaderboard"]["entries"], 4)
        self.assertEqual(
            manifest["pilotLeaderboard"]["source"], "real-frontier-run-honest-scoring"
        )
        self.assertFalse(manifest["hostedRunnerIncluded"])
        self.assertFalse(manifest["billingCheckoutConnected"])

        for relative_path in [
            "index.html",
            "report.html",
            "leaderboard.html",
            "report.json",
            "leaderboard.json",
            "public-demo.json",
        ]:
            self.assertTrue((self.tmpdir / relative_path).exists(), relative_path)

        index_html = (self.tmpdir / "index.html").read_text(encoding="utf-8")
        report_html = (self.tmpdir / "report.html").read_text(encoding="utf-8")
        leaderboard_html = (self.tmpdir / "leaderboard.html").read_text(encoding="utf-8")
        self.assertIn("Static local-public sample", index_html)
        self.assertIn("Offline Demo Agent", index_html)
        self.assertIn("Overall 98.88", report_html)
        self.assertIn("5/5 tasks", report_html)
        # Honest frontier ranking is surfaced on the public leaderboard.
        self.assertIn("Honest frontier leaderboard", leaderboard_html)
        self.assertIn("Claude Code (Opus 4.8)", leaderboard_html)
        self.assertIn("Claude Code (Sonnet 4.6)", leaderboard_html)
        self.assertIn("Claude Code (Haiku 4.5)", leaderboard_html)
        self.assertIn("local-public", leaderboard_html)
        self.assertNotIn(str(self.tmpdir), index_html + report_html + leaderboard_html)

    def test_public_demo_generator_is_idempotent_for_committed_static_files(self) -> None:
        build_public_demo_site(REPO_ROOT, self.tmpdir)
        first_snapshot = {
            path.relative_to(self.tmpdir): path.read_bytes()
            for path in sorted(self.tmpdir.rglob("*"))
            if path.is_file()
        }

        build_public_demo_site(REPO_ROOT, self.tmpdir)
        second_snapshot = {
            path.relative_to(self.tmpdir): path.read_bytes()
            for path in sorted(self.tmpdir.rglob("*"))
            if path.is_file()
        }

        self.assertEqual(first_snapshot, second_snapshot)

    def test_committed_public_demo_site_is_present_on_launch_surface(self) -> None:
        demo_dir = REPO_ROOT / "site/demo"
        self.assertTrue((demo_dir / "index.html").exists())
        self.assertTrue((demo_dir / "report.html").exists())
        self.assertTrue((demo_dir / "leaderboard.html").exists())
        self.assertTrue((demo_dir / "public-demo.json").exists())

        demo_manifest = json.loads((demo_dir / "public-demo.json").read_text(encoding="utf-8"))
        self.assertEqual(demo_manifest["status"], "static-local-public-sample-ready")
        self.assertEqual(demo_manifest["sampleRun"]["overall"], 98.88)
        # Committed public leaderboard is the honest real frontier run (4 entries).
        self.assertEqual(demo_manifest["pilotLeaderboard"]["entries"], 4)
        self.assertEqual(
            demo_manifest["pilotLeaderboard"]["source"], "real-frontier-run-honest-scoring"
        )

        launch_html = (REPO_ROOT / "site/index.html").read_text(encoding="utf-8")
        launch_json = json.loads((REPO_ROOT / "site/launch.json").read_text(encoding="utf-8"))
        self.assertIn("Open sample report", launch_html)
        self.assertIn("site/demo/report.html", launch_html)
        self.assertEqual(launch_json["publicDemoSample"], "static-local-public-ready")


if __name__ == "__main__":
    unittest.main()
