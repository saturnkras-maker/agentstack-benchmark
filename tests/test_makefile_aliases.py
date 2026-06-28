from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class MakefileAliasTests(unittest.TestCase):
    def test_makefile_exposes_local_mvp_aliases(self) -> None:
        makefile = REPO_ROOT / "Makefile"
        self.assertTrue(makefile.exists())
        text = makefile.read_text()
        for target in [
            "doctor:",
            "local-model-check:",
            "demo-local:",
            "demo-local-once:",
            "demo-local-auto:",
            "demo-local-auto-once:",
            "demo-pilots:",
            "verify-local-mvp:",
            "public-demo-site:",
            "cockpit:",
            "serve:",
            "test:",
            "compile:",
        ]:
            self.assertIn(target, text)
        self.assertIn("agentstack_benchmark.cli doctor", text)
        self.assertIn("agentstack_benchmark.cli serve", text)
        self.assertIn("agentstack_benchmark.cli demo-local", text)
        self.assertIn("agentstack_benchmark.cli pilot-run", text)
        self.assertIn("agentstack_benchmark.cli verify-local-mvp", text)
        self.assertIn("agentstack_benchmark.cli public-demo-site", text)
        # PYTHON prefers python3.11 but falls back to python3 when 3.11 is absent.
        self.assertIn("PYTHON ?=", text)
        self.assertIn("python3.11", text)
        self.assertIn("--agent-mode auto-local-model", text)

    def test_make_doctor_smoke_prints_ready_json(self) -> None:
        result = subprocess.run(
            ["make", "doctor", "DOCTOR_ARGS=--skip-local-model-probe"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
            timeout=20,
        )

        self.assertIn('"status": "ready"', result.stdout)
        self.assertIn('"doesNotStartServers": true', result.stdout)
        self.assertIn("demo-local", result.stdout)


if __name__ == "__main__":
    unittest.main()
