from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublicLaunchSiteTests(unittest.TestCase):
    def test_site_points_to_one_command_offline_mvp_demo(self) -> None:
        html = (REPO_ROOT / "site/index.html").read_text(encoding="utf-8")

        self.assertIn("One-command offline demo", html)
        self.assertIn("demo-local", html)
        self.assertIn("No internet", html)
        self.assertIn("No API keys", html)
        self.assertIn("Optional local model adapter", html)
        self.assertIn("First-run doctor", html)
        self.assertIn("agentstack_benchmark.cli doctor", html)
        self.assertIn("local-model-check", html)
        self.assertIn("auto-local-model", html)
        self.assertIn("http://127.0.0.1:8088/run", html)
        self.assertNotIn("pull/1", html)
        self.assertNotIn("PR #1", html)

    def test_launch_json_declares_offline_mvp_demo_ready_without_secrets(self) -> None:
        body = json.loads((REPO_ROOT / "site/launch.json").read_text(encoding="utf-8"))

        self.assertEqual(body["releaseBranch"], "main")
        self.assertEqual(body["offlineLocalDemo"], "ready")
        self.assertEqual(body["browserRunUx"], "loopback-local-ready")
        self.assertEqual(body["localModelAdapter"], "loopback-autodetect-ready")
        self.assertEqual(body["firstRunDoctor"], "ready")
        self.assertEqual(body["localModelFallback"], "deterministic-offline-demo")
        self.assertEqual(body["internetRequiredForDemo"], False)
        self.assertEqual(body["apiKeysRequiredForDemo"], False)
        self.assertEqual(body["secretsEmbedded"], False)
        self.assertEqual(body["billingCheckoutConnected"], False)
        self.assertNotIn("pullRequest", body)


if __name__ == "__main__":
    unittest.main()
