from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import request

from agentstack_benchmark.runner import run_benchmark
from agentstack_benchmark.server import make_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class APIServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-benchmark-api-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _start_server(self):
        server = make_server("127.0.0.1", 0, self.tmpdir / "runs")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        return server

    def _get_json(self, path: str) -> dict:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        with request.urlopen(url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.loads(response.read().decode("utf-8"))

    def test_healthz_declares_free_beta_mode(self) -> None:
        self._server = self._start_server()

        body = self._get_json("/api/v1/healthz")

        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "agentstack-benchmark")
        self.assertEqual(body["pricingMode"], "free-beta")

    def test_leaderboard_endpoint_returns_ranked_runs(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        body = self._get_json("/api/v1/leaderboard")

        self.assertEqual(body["pricingMode"], "free-beta")
        self.assertEqual(len(body["entries"]), 2)
        self.assertEqual(body["entries"][0]["rank"], 1)
        self.assertEqual(body["entries"][0]["agentId"], "mock-good-agent")
        self.assertGreater(body["entries"][0]["overall"], body["entries"][1]["overall"])


if __name__ == "__main__":
    unittest.main()
