from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentstack_benchmark.beta_package import (
    PUBLIC_BETA_PACKAGE_SCHEMA_VERSION,
    build_public_beta_package,
)
from agentstack_benchmark.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicBetaPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-beta-package-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_public_beta_package_manifest_covers_release_critical_assets(self) -> None:
        package = build_public_beta_package(REPO_ROOT, self.tmpdir)
        manifest = json.loads((self.tmpdir / "public_beta_manifest.json").read_text())

        self.assertEqual(package["schemaVersion"], PUBLIC_BETA_PACKAGE_SCHEMA_VERSION)
        self.assertEqual(manifest["schemaVersion"], PUBLIC_BETA_PACKAGE_SCHEMA_VERSION)
        self.assertEqual(manifest["pricingMode"], "free-beta")
        self.assertEqual(manifest["defaultTrack"], "local-public")
        self.assertEqual(manifest["hostedVerifiedStatus"], "reserved-server-side-only")
        self.assertEqual(manifest["deploymentStatus"], "local-artifact-not-deployed")
        self.assertEqual(manifest["billingStatus"], "deferred-no-payment-flow")
        self.assertFalse(manifest["launchActionsPerformed"])

        asset_paths = {asset["path"] for asset in manifest["assets"]}
        expected_paths = {
            "README.md",
            "Makefile",
            "pyproject.toml",
            "docs/product-technical-spec-v0.1.md",
            "docs/monetization-v0.md",
            "docs/adapter-contract-v0.1.md",
            "docs/scoring-schema-v1.md",
            "docs/reproducibility-redaction.md",
            "docs/local-public-pilots-v0.1.md",
            "docs/hosted-verified-track-v0.1.md",
            "docs/auth-rate-limit-v0.1.md",
            "docs/public-beta-package-v0.1.md",
            "docs/offline-local-mvp-demo.md",
            "docs/local-model-adapter-v0.1.md",
            "docs/first-run-doctor-v0.1.md",
            "docs/local-mvp-cockpit-v0.1.md",
            "docs/local-mvp-verification-v0.1.md",
            "docs/public-demo-sample-v0.1.md",
            "examples/manifests/offline_demo.json",
            "examples/task_packs/beta_v0_1.json",
            "examples/pilots/local_public_v0_1.json",
            "site/demo/index.html",
            "site/demo/report.html",
            "site/demo/leaderboard.html",
            "site/demo/public-demo.json",
        }
        self.assertTrue(expected_paths.issubset(asset_paths))
        for asset in manifest["assets"]:
            self.assertRegex(asset["sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse(Path(asset["path"]).is_absolute())

    def test_public_beta_checklist_preserves_no_deploy_no_billing_boundary(self) -> None:
        build_public_beta_package(REPO_ROOT, self.tmpdir)
        checklist = (self.tmpdir / "PUBLIC_BETA_CHECKLIST.md").read_text()

        self.assertIn("# AgentStack Benchmark public beta package", checklist)
        self.assertIn("No external deploy has been performed", checklist)
        self.assertIn("No billing/payment flow is included", checklist)
        self.assertIn("PYTHONPATH=src python3 -m unittest discover -s tests -v", checklist)
        self.assertIn("agentstack_benchmark.cli pilot-run", checklist)
        self.assertIn("agentstack_benchmark.cli serve", checklist)
        self.assertIn("agentstack_benchmark.cli demo-local", checklist)
        self.assertIn("agentstack_benchmark.cli local-model-check", checklist)
        self.assertIn("agentstack_benchmark.cli doctor", checklist)
        self.assertIn("make doctor", checklist)
        self.assertIn("make demo-local", checklist)
        self.assertIn("auto-local-model", checklist)
        self.assertIn("Offline local MVP demo", checklist)
        self.assertIn("local model adapter", checklist.lower())
        self.assertIn("Local MVP Cockpit", checklist)
        self.assertIn("make cockpit", checklist)
        self.assertIn("make verify-local-mvp", checklist)
        self.assertIn("make demo-pilots", checklist)
        self.assertIn("Static public demo report", checklist)
        self.assertNotIn("git push", checklist)
        self.assertNotIn("--force", checklist)
        self.assertNotIn("private key", checklist.lower())

    def test_public_beta_package_cli_writes_manifest_and_safe_summary(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = cli_main(["beta-package", "--out-dir", str(self.tmpdir)])

        self.assertEqual(exit_code, 0)
        cli_payload = json.loads(stdout.getvalue())
        self.assertEqual(cli_payload["packageStatus"], "local-ready")
        manifest = json.loads((self.tmpdir / "public_beta_manifest.json").read_text())
        summary = json.loads((self.tmpdir / "summary.json").read_text())
        self.assertEqual(summary["packageStatus"], "local-ready")
        self.assertEqual(summary["manifestPath"], str(self.tmpdir / "public_beta_manifest.json"))
        self.assertGreaterEqual(summary["assetCount"], 12)
        self.assertNotIn("token", json.dumps(manifest).lower())
        self.assertNotIn("secret", json.dumps(manifest).lower())


if __name__ == "__main__":
    unittest.main()
