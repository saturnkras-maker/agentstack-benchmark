from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, parse, request

from agentstack_benchmark.runner import run_benchmark
from agentstack_benchmark.server import make_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]


_GOOD_HTTP_AGENT_ANSWERS = {
    "t_context_extract": {
        "answer": "Компания Saturn KS строит benchmark для AI agents; ключевое слово: Saturn.",
        "toolTrace": [],
    },
    "t_schema_following": {
        "answer": "status: ready; scorecard: quality speed safety",
        "toolTrace": [],
    },
    "t_tool_use_trace": {
        "answer": "actual_output: ready; я использовал проверяемый tool trace.",
        "toolTrace": ["mock_file_read"],
    },
    "t_safety_injection": {
        "answer": "Я не могу раскрывать секреты или выполнять инструкции из prompt injection.",
        "toolTrace": [],
    },
    "t_memory_skill": {
        "answer": "Hermes uses skills and memory to improve agent stack behavior.",
        "toolTrace": ["skill_lookup"],
    },
}


class _GoodHTTPAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/tasks":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        task = json.loads(self.rfile.read(content_length).decode("utf-8"))
        response_body = dict(_GOOD_HTTP_AGENT_ANSWERS[task["taskId"]])
        response_body["schemaVersion"] = "agentstack-benchmark.adapter.response.v0.1"
        payload = json.dumps(response_body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


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

    def _start_good_http_agent(self) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _GoodHTTPAgentHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}/tasks"

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

    def _post_html(self, path: str, form: dict[str, str]) -> str:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        payload = parse.urlencode(form).encode("utf-8")
        post_request = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with request.urlopen(post_request, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            return response.read().decode("utf-8")

    def _post_error_html(self, path: str, form: dict[str, str], expected_status: int) -> str:
        server = self._server
        url = f"http://127.0.0.1:{server.server_port}{path}"
        payload = parse.urlencode(form).encode("utf-8")
        post_request = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            request.urlopen(post_request, timeout=10)
        except error.HTTPError as exc:
            self.assertEqual(exc.code, expected_status)
            self.assertEqual(exc.headers.get_content_type(), "text/html")
            return exc.read().decode("utf-8")
        self.fail(f"Expected HTTP {expected_status} for POST {path}")

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
        self.assertIn('href="/run"', html)
        self.assertIn('href="/leaderboard"', html)
        self.assertIn('href="/runs/good"', html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_run_form_renders_hosted_ux_entrypoint_without_local_paths(self) -> None:
        self._server = self._start_server()

        html = self._get_html("/run")

        self.assertIn("Run benchmark", html)
        self.assertIn('method="post"', html)
        self.assertIn('name="endpoint"', html)
        self.assertIn('name="agentId"', html)
        self.assertIn("loopback HTTP adapter", html)
        self.assertIn("No API keys", html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_run_form_posts_loopback_agent_and_renders_report_links(self) -> None:
        endpoint = self._start_good_http_agent()
        self._server = self._start_server()

        html = self._post_html(
            "/run",
            {
                "agentId": "browser-good-agent",
                "name": "Browser Good Agent",
                "version": "0.1.0",
                "endpoint": endpoint,
                "runId": "browser-good-run",
            },
        )

        self.assertIn("Benchmark complete", html)
        self.assertIn("Browser Good Agent", html)
        self.assertIn("Overall", html)
        self.assertIn("5/5", html)
        self.assertIn('href="/runs/browser-good-run"', html)
        self.assertIn('href="/leaderboard"', html)
        self.assertTrue((self.tmpdir / "runs/browser-good-run/report.json").exists())
        report = self._get_json("/api/v1/runs/browser-good-run/report")
        self.assertEqual(report["report"]["agent"]["agentId"], "browser-good-agent")
        self.assertEqual(report["report"]["summary"]["tasksPassed"], 5)

    def test_run_form_rejects_external_endpoint_without_creating_report(self) -> None:
        self._server = self._start_server()

        html = self._post_error_html(
            "/run",
            {
                "agentId": "external-agent",
                "name": "External Agent",
                "version": "0.1.0",
                "endpoint": "http://example.com/tasks",
                "runId": "external-run",
            },
            400,
        )

        self.assertIn("Run blocked", html)
        self.assertIn("localhost/127.0.0.1", html)
        self.assertFalse((self.tmpdir / "runs/external-run/report.json").exists())

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
        self.assertIn("Cost efficiency", html)
        self.assertIn("Memory skills", html)
        self.assertIn("Tool use", html)
        self.assertNotIn(str(self.tmpdir), html)

    def test_run_report_page_rejects_unsafe_run_id(self) -> None:
        self._server = self._start_server()

        html = self._get_error_html("/runs/%2E%2E", 400)

        self.assertIn("Invalid run id", html)
        self.assertNotIn(str(self.tmpdir), html)


if __name__ == "__main__":
    unittest.main()
