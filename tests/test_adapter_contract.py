from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agentstack_benchmark.adapter_contract import (
    ADAPTER_CONTRACT_VERSION,
    ADAPTER_REQUEST_SCHEMA_VERSION,
    ADAPTER_RESPONSE_SCHEMA_VERSION,
    build_adapter_contract,
    build_task_request,
    normalize_agent_response,
)
from agentstack_benchmark.cli import main as cli_main
from agentstack_benchmark.runner import run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-adapter-contract-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_task_request_is_versioned_and_does_not_leak_expected_answer(self) -> None:
        task = {
            "taskId": "contract_task",
            "category": "tool-use",
            "prompt": "Read the provided context and answer.",
            "context": {"safeFact": "visible"},
            "timeoutSeconds": 7,
            "expected": {"type": "contains", "value": "secret expected answer"},
            "budgetUsd": 0.02,
        }

        payload = build_task_request(task)

        self.assertEqual(
            list(payload),
            ["schemaVersion", "taskId", "category", "prompt", "context", "timeoutSeconds"],
        )
        self.assertEqual(payload["schemaVersion"], ADAPTER_REQUEST_SCHEMA_VERSION)
        self.assertEqual(payload["taskId"], "contract_task")
        self.assertEqual(payload["category"], "tool-use")
        self.assertEqual(payload["context"], {"safeFact": "visible"})
        self.assertEqual(payload["timeoutSeconds"], 7)
        self.assertNotIn("expected", payload)
        self.assertNotIn("budgetUsd", payload)
        self.assertNotIn("secret expected answer", json.dumps(payload, ensure_ascii=False))

    def test_http_adapter_receives_contract_payload_for_each_task(self) -> None:
        received_payloads: list[dict] = []

        class ContractHTTPAgent(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                received_payloads.append(payload)
                response = json.dumps(
                    {"schemaVersion": ADAPTER_RESPONSE_SCHEMA_VERSION, "answer": "ok", "toolTrace": []},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format: str, *args: object) -> None:
                return

        task_pack = {
            "taskPackId": "contract-pack",
            "name": "Contract Pack",
            "version": "0.1.0",
            "tasks": [
                {
                    "taskId": "contract_task_a",
                    "category": "core",
                    "prompt": "Say ok.",
                    "context": {"visible": True},
                    "timeoutSeconds": 3,
                    "expected": {"type": "contains", "value": "ok"},
                },
                {
                    "taskId": "contract_task_b",
                    "category": "safety",
                    "prompt": "Say ok safely.",
                    "expected": {"type": "contains", "value": "ok"},
                },
            ],
        }
        task_pack_path = self.tmpdir / "contract_pack.json"
        task_pack_path.write_text(json.dumps(task_pack), encoding="utf-8")

        server = HTTPServer(("127.0.0.1", 0), ContractHTTPAgent)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            manifest = {
                "agentId": "contract-http-agent",
                "name": "Contract HTTP Agent",
                "version": "0.1.0",
                "adapter": {
                    "type": "http",
                    "endpoint": f"http://127.0.0.1:{server.server_port}/tasks",
                },
                "limits": {"timeoutSecondsPerTask": 5, "maxRunsPerTask": 1},
            }
            manifest_path = self.tmpdir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            report = run_benchmark(manifest_path, task_pack_path, self.tmpdir / "run")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(report["summary"]["tasksPassed"], 2)
        self.assertEqual([payload["taskId"] for payload in received_payloads], ["contract_task_a", "contract_task_b"])
        self.assertTrue(all(payload["schemaVersion"] == ADAPTER_REQUEST_SCHEMA_VERSION for payload in received_payloads))
        self.assertEqual(received_payloads[0]["timeoutSeconds"], 3)
        self.assertEqual(received_payloads[1]["timeoutSeconds"], 5)
        self.assertTrue(all("expected" not in payload for payload in received_payloads))

    def test_response_normalization_enforces_documented_shape(self) -> None:
        valid = normalize_agent_response(
            {
                "schemaVersion": ADAPTER_RESPONSE_SCHEMA_VERSION,
                "answer": "ready",
                "toolTrace": ["file_read"],
                "costUsd": 0.001,
            }
        )
        self.assertEqual(valid["answer"], "ready")
        self.assertEqual(valid["toolTrace"], ["file_read"])
        self.assertEqual(valid["costUsd"], 0.001)

        invalid = normalize_agent_response({"answer": {"nested": "not allowed"}, "toolTrace": ["ok"]})
        self.assertEqual(invalid["answer"], "")
        self.assertEqual(invalid["toolTrace"], [])
        self.assertIn("invalid_adapter_response", invalid["runtimeError"])

        invalid_trace = normalize_agent_response({"answer": "ready", "toolTrace": ["ok", 3]})
        self.assertEqual(invalid_trace["answer"], "")
        self.assertEqual(invalid_trace["toolTrace"], [])
        self.assertIn("toolTrace", invalid_trace["runtimeError"])

    def test_adapter_contract_is_machine_readable_and_available_from_cli(self) -> None:
        contract = build_adapter_contract()

        self.assertEqual(contract["schemaVersion"], ADAPTER_CONTRACT_VERSION)
        self.assertEqual(contract["request"]["schemaVersion"], ADAPTER_REQUEST_SCHEMA_VERSION)
        self.assertEqual(contract["response"]["schemaVersion"], ADAPTER_RESPONSE_SCHEMA_VERSION)
        self.assertEqual(contract["request"]["required"], ["schemaVersion", "taskId", "category", "prompt", "context", "timeoutSeconds"])
        self.assertEqual(contract["response"]["required"], ["answer", "toolTrace"])
        self.assertTrue(contract["safety"]["localOnly"])

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = cli_main(["adapter-contract"])
        cli_contract = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(cli_contract, contract)


if __name__ == "__main__":
    unittest.main()
