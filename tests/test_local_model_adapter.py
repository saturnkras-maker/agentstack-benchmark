from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agentstack_benchmark.cli import main
from agentstack_benchmark.local_model import (
    discover_local_model_backend,
    run_local_model_demo_once,
)
from agentstack_benchmark.offline_demo import OFFLINE_DEMO_AGENT_ANSWERS


class FakeOpenAICompatibleHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json({"data": [{"id": "fake-local-model"}]})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(content_length).decode("utf-8"))
        prompt = "\n".join(message.get("content", "") for message in body.get("messages", []))
        task_id = "unknown"
        for candidate in OFFLINE_DEMO_AGENT_ANSWERS:
            if candidate in prompt:
                task_id = candidate
                break
        answer = OFFLINE_DEMO_AGENT_ANSWERS.get(task_id, {"answer": "unknown task"})["answer"]
        self._send_json({"choices": [{"message": {"content": answer}}]})

    def _send_json(self, body: dict[str, Any]) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


class FakeLocalModelServer:
    def __enter__(self) -> "FakeLocalModelServer":
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAICompatibleHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class LocalModelAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-local-model-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_discovery_accepts_loopback_openai_compatible_endpoint(self) -> None:
        with FakeLocalModelServer() as fake:
            backend = discover_local_model_backend(base_url=fake.base_url, env={})

        self.assertTrue(backend.available)
        self.assertEqual(backend.provider, "openai-compatible")
        self.assertEqual(backend.base_url, fake.base_url)
        self.assertEqual(backend.model, "fake-local-model")
        self.assertEqual(backend.internetRequired, False)
        self.assertEqual(backend.apiKeysRequired, False)

    def test_discovery_rejects_external_endpoints_without_network_call(self) -> None:
        backend = discover_local_model_backend(base_url="https://models.example.com/v1", env={})

        self.assertFalse(backend.available)
        self.assertEqual(backend.reason, "local-model-endpoint-must-be-loopback")
        self.assertEqual(backend.internetRequired, False)
        self.assertEqual(backend.apiKeysRequired, False)

    def test_local_model_demo_runs_against_fake_openai_backend(self) -> None:
        with FakeLocalModelServer() as fake:
            summary = run_local_model_demo_once(
                backend=discover_local_model_backend(base_url=fake.base_url, env={}),
                runs_dir=self.tmpdir / "runs",
                run_id="fake-local-model-run",
                agent_port=0,
            )

        report_path = self.tmpdir / "runs/fake-local-model-run/report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["mode"], "local-model-demo")
        self.assertEqual(summary["localModelProvider"], "openai-compatible")
        self.assertEqual(summary["internetRequired"], False)
        self.assertEqual(summary["apiKeysRequired"], False)
        self.assertEqual(report["agent"]["agentId"], "local-model-agent")
        self.assertEqual(report["summary"]["tasksPassed"], 5)
        self.assertGreater(report["summary"]["overall"], 90)

    def test_local_model_check_cli_reports_backend_status(self) -> None:
        with FakeLocalModelServer() as fake:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["local-model-check", "--base-url", fake.base_url])

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout.getvalue())
        self.assertEqual(body["available"], True)
        self.assertEqual(body["provider"], "openai-compatible")
        self.assertEqual(body["model"], "fake-local-model")
        self.assertEqual(body["internetRequired"], False)
        self.assertEqual(body["apiKeysRequired"], False)

    def test_demo_local_auto_mode_falls_back_without_available_backend(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "demo-local",
                    "--once",
                    "--agent-mode",
                    "auto-local-model",
                    "--local-model-base-url",
                    "http://127.0.0.1:9/v1",
                    "--agent-port",
                    "0",
                    "--ui-port",
                    "8098",
                    "--runs-dir",
                    str(self.tmpdir / "fallback-runs"),
                    "--run-id",
                    "fallback-run",
                ]
            )

        self.assertEqual(exit_code, 0)
        body = json.loads(stdout.getvalue())
        self.assertEqual(body["mode"], "offline-local-demo")
        self.assertEqual(body["fallbackFromLocalModel"], True)
        self.assertEqual(body["localModelStatus"]["available"], False)
        self.assertEqual(body["internetRequired"], False)
        self.assertEqual(body["apiKeysRequired"], False)


if __name__ == "__main__":
    unittest.main()
