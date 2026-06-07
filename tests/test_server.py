from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import error, request

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

    def _get_html(self, path: str) -> str:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        with request.urlopen(url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            return response.read().decode("utf-8")

    def _get_error_json(self, path: str, expected_status: int) -> dict:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        try:
            request.urlopen(url, timeout=5)
        except error.HTTPError as exc:
            self.assertEqual(exc.code, expected_status)
            self.assertEqual(exc.headers.get_content_type(), "application/json")
            return json.loads(exc.read().decode("utf-8"))
        self.fail(f"Expected HTTP {expected_status} for {path}")

    def _get_error_html(self, path: str, expected_status: int) -> str:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        try:
            request.urlopen(url, timeout=5)
        except error.HTTPError as exc:
            self.assertEqual(exc.code, expected_status)
            self.assertEqual(exc.headers.get_content_type(), "text/html")
            return exc.read().decode("utf-8")
        self.fail(f"Expected HTTP {expected_status} for {path}")

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
        self.assertEqual(body["entries"][0]["track"], "local-public")
        self.assertGreater(body["entries"][0]["overall"], body["entries"][1]["overall"])

    def test_runs_endpoint_lists_existing_report_summaries(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        body = self._get_json("/api/v1/runs")

        self.assertEqual(body["pricingMode"], "free-beta")
        self.assertEqual([run["runId"] for run in body["runs"]], ["bad", "good"])
        good_run = body["runs"][1]
        self.assertEqual(good_run["agentId"], "mock-good-agent")
        self.assertEqual(good_run["track"], "local-public")
        self.assertGreater(good_run["overall"], 90)
        self.assertEqual(good_run["tasksTotal"], 5)
        self.assertNotIn("attempts", good_run)

    def test_run_report_endpoint_returns_one_existing_report(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        body = self._get_json("/api/v1/runs/good/report")

        self.assertEqual(body["pricingMode"], "free-beta")
        self.assertEqual(body["runId"], "good")
        self.assertEqual(body["track"], "local-public")
        report = body["report"]
        self.assertEqual(report["track"], "local-public")
        self.assertEqual(report["agent"]["agentId"], "mock-good-agent")
        self.assertEqual(report["summary"]["tasksTotal"], 5)
        self.assertIn("attempts", report)

    def test_run_report_endpoint_rejects_unsafe_run_id(self) -> None:
        self._server = self._start_server()

        body = self._get_error_json("/api/v1/runs/%2E%2E/report", 400)

        self.assertEqual(body["error"]["code"], "INVALID_RUN_ID")

    def test_home_page_renders_public_beta_preview_without_local_paths(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        html = self._get_html("/")

        self.assertIn("AgentStack Benchmark", html)
        self.assertIn("Free beta", html)
        self.assertIn("2 local runs", html)
        self.assertIn('href="/leaderboard"', html)
        self.assertIn('href="/runs/good"', html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_leaderboard_page_renders_ranked_html_preview(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        html = self._get_html("/leaderboard")

        self.assertIn("Leaderboard", html)
        self.assertLess(html.index("Mock Good Agent"), html.index("Mock Bad Agent"))
        self.assertIn("#1", html)
        self.assertIn("local-public", html)
        self.assertIn('class="track-badge"', html)
        self.assertIn('href="/runs/good"', html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_run_report_page_renders_existing_report_without_local_paths(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")
        self._server = self._start_server()

        html = self._get_html("/runs/good")

        self.assertIn("Run report", html)
        self.assertIn("Mock Good Agent", html)
        self.assertIn("Overall", html)
        self.assertIn("local-public", html)
        self.assertIn('class="track-badge"', html)
        self.assertIn("5/5 tasks", html)
        self.assertIn("Back to leaderboard", html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_run_report_page_rejects_unsafe_run_id(self) -> None:
        self._server = self._start_server()

        html = self._get_error_html("/runs/%2E%2E", 400)

        self.assertIn("Invalid run id", html)
        self.assertNotIn(str(self.tmpdir), html)


if __name__ == "__main__":
    unittest.main()
