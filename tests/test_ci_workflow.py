from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CIWorkflowTests(unittest.TestCase):
    def test_github_actions_ci_runs_local_mvp_trust_gates_without_secrets(self) -> None:
        workflow = REPO_ROOT / ".github/workflows/ci.yml"
        self.assertTrue(workflow.exists())
        text = workflow.read_text(encoding="utf-8")

        self.assertIn("Public beta trust gates", text)
        self.assertIn("python-version: '3.11'", text)
        self.assertIn("python -m unittest discover -s tests -v", text)
        self.assertIn("python -m compileall -q src examples tests", text)
        self.assertIn("make demo-local-once", text)
        self.assertIn("make verify-local-mvp", text)
        self.assertIn("grep -R", text)
        self.assertNotIn("STRIPE_SECRET_KEY", text)
        self.assertNotIn("GITHUB_TOKEN:", text)
        self.assertNotIn("secrets.", text)


if __name__ == "__main__":
    unittest.main()
