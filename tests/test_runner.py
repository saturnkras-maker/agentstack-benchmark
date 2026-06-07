from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agentstack_benchmark.leaderboard import build_leaderboard
from agentstack_benchmark.runner import run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-benchmark-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_good_agent_scores_higher_than_bad_agent(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        good = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            task_pack,
            self.tmpdir / "good",
        )
        bad = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_bad.json",
            task_pack,
            self.tmpdir / "bad",
        )

        self.assertGreater(good["summary"]["overall"], 90)
        self.assertLess(bad["summary"]["overall"], 25)
        self.assertGreater(good["summary"]["overall"], bad["summary"]["overall"])
        self.assertTrue((self.tmpdir / "good/report.json").exists())
        self.assertTrue((self.tmpdir / "good/report.md").exists())

    def test_report_contains_manifest_and_task_pack_hashes(self) -> None:
        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )
        self.assertEqual(len(report["agent"]["manifestHash"]), 64)
        self.assertEqual(len(report["taskPack"]["taskPackHash"]), 64)

    def test_report_declares_local_public_track_with_canonical_order(self) -> None:
        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )

        self.assertEqual(list(report)[:4], ["schemaVersion", "track", "agent", "taskPack"])
        self.assertEqual(report["track"], "local-public")
        self.assertNotEqual(report["track"], "hosted-verified")

        persisted = json.loads((self.tmpdir / "good/report.json").read_text(encoding="utf-8"))
        self.assertEqual(list(persisted)[:4], ["schemaVersion", "track", "agent", "taskPack"])
        self.assertEqual(persisted["track"], "local-public")

    def test_report_declares_scoring_schema_v1_with_canonical_order(self) -> None:
        from agentstack_benchmark.evaluator import SCORING_SCHEMA_VERSION, SCORING_WEIGHTS

        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )

        self.assertEqual(
            list(report)[:6],
            ["schemaVersion", "track", "agent", "taskPack", "scoringSchema", "summary"],
        )
        self.assertEqual(report["scoringSchema"]["schemaVersion"], SCORING_SCHEMA_VERSION)
        self.assertEqual(report["scoringSchema"]["weights"], SCORING_WEIGHTS)
        self.assertEqual(sum(report["scoringSchema"]["weights"].values()), 1.0)
        self.assertEqual(
            report["scoringSchema"]["verdicts"],
            ["PASS", "PARTIAL", "FAIL", "INVALID_RUN"],
        )

        persisted = json.loads((self.tmpdir / "good/report.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["scoringSchema"], report["scoringSchema"])

    def test_markdown_report_contains_scorecard_context_and_task_scores(self) -> None:
        run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )

        markdown = (self.tmpdir / "good/report.md").read_text(encoding="utf-8")

        self.assertIn("Track: `local-public`", markdown)
        self.assertIn("Scoring schema: `scoring_schema_v1`", markdown)
        self.assertIn("## Scorecard", markdown)
        self.assertIn("- quality (weight 0.30):", markdown)
        self.assertIn("- reliability (weight 0.15):", markdown)
        self.assertIn("## Task attempts", markdown)
        self.assertIn("scores: quality=100.0", markdown)
        self.assertIn("toolUse=100.0", markdown)

    def test_report_contains_reproducibility_hash_that_depends_on_track(self) -> None:
        from agentstack_benchmark.reproducibility import compute_report_artifact_hash

        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )

        reproducibility = report["reproducibility"]
        self.assertEqual(reproducibility["hashAlgorithm"], "sha256")
        self.assertEqual(len(reproducibility["artifactHash"]), 64)
        self.assertEqual(
            reproducibility["hashFields"][:5],
            ["schemaVersion", "track", "agent", "taskPack", "scoringSchema"],
        )

        hash_input = {field: report[field] for field in reproducibility["hashFields"]}
        self.assertEqual(hash_input["track"], "local-public")
        self.assertEqual(compute_report_artifact_hash(hash_input), reproducibility["artifactHash"])
        hosted_hash_input = dict(hash_input, track="hosted-verified")
        self.assertNotEqual(
            compute_report_artifact_hash(hosted_hash_input),
            reproducibility["artifactHash"],
        )

    def test_report_contains_score_variance_and_confidence_band(self) -> None:
        report = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
            self.tmpdir / "good",
        )

        score_stats = report["reproducibility"]["scoreStats"]
        band = score_stats["confidenceBand"]

        self.assertEqual(score_stats["sampleSize"], len(report["attempts"]))
        self.assertGreaterEqual(score_stats["taskScoreVariance"], 0.0)
        self.assertGreaterEqual(score_stats["taskScoreStdDev"], 0.0)
        self.assertEqual(band["confidenceLevel"], 0.95)
        self.assertLessEqual(band["lower"], report["summary"]["overall"])
        self.assertGreaterEqual(band["upper"], report["summary"]["overall"])
        self.assertGreaterEqual(band["lower"], 0.0)
        self.assertLessEqual(band["upper"], 100.0)

    def test_report_redacts_secret_like_adapter_output_before_persisting(self) -> None:
        marker_parts = {
            "api_key": "api_key=" + "sk-" + "live-" + "123",
            "token": "token=" + "abc" + "123",
            "password": "password: " + "hunter" + "2",
            "secret": "secret=" + "hidden",
            "ru_password": "пароль: " + "мед" + "ведь",
            "trace_token": "token=" + "trace-" + "secret",
        }
        agent_script = self.tmpdir / "leaky_agent.py"
        agent_script.write_text(
            f"""
import json
import sys

json.loads(sys.stdin.read())
print(json.dumps({{
    "answer": (
        "safe answer {marker_parts['api_key']} {marker_parts['token']} "
        "{marker_parts['password']} {marker_parts['secret']} {marker_parts['ru_password']}"
    ),
    "toolTrace": ["used {marker_parts['trace_token']}"],
}}))
""".strip(),
            encoding="utf-8",
        )
        manifest = {
            "agentId": "leaky-agent",
            "name": "Leaky Agent",
            "version": "0.1.0",
            "adapter": {"type": "cli", "command": ["python3", str(agent_script)]},
            "limits": {"timeoutSecondsPerTask": 5, "maxRunsPerTask": 1},
        }
        task_pack = {
            "taskPackId": "redaction-pack",
            "name": "Redaction Pack",
            "version": "0.1.0",
            "tasks": [
                {
                    "taskId": "redact_secret_answer",
                    "category": "core",
                    "prompt": "Return safe answer.",
                    "expected": {"type": "contains", "value": "safe answer"},
                }
            ],
        }
        manifest_path = self.tmpdir / "leaky_manifest.json"
        task_pack_path = self.tmpdir / "redaction_pack.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        task_pack_path.write_text(json.dumps(task_pack), encoding="utf-8")

        report = run_benchmark(manifest_path, task_pack_path, self.tmpdir / "leaky-run")
        persisted_json = (self.tmpdir / "leaky-run/report.json").read_text(encoding="utf-8")
        persisted_md = (self.tmpdir / "leaky-run/report.md").read_text(encoding="utf-8")

        self.assertEqual(report["attempts"][0]["verdict"], "PASS")
        self.assertIn("[REDACTED]", report["attempts"][0]["answer"])
        self.assertGreaterEqual(report["reproducibility"]["redaction"]["redactedOccurrences"], 5)
        for leaked in marker_parts.values():
            self.assertNotIn(leaked, persisted_json)
            self.assertNotIn(leaked, persisted_md)

    def test_run_track_enum_is_closed(self) -> None:
        from agentstack_benchmark.schemas import (
            ALLOWED_RUN_TRACKS,
            RUN_TRACK_HOSTED_VERIFIED,
            RUN_TRACK_LOCAL_PUBLIC,
        )

        self.assertEqual(RUN_TRACK_LOCAL_PUBLIC, "local-public")
        self.assertEqual(RUN_TRACK_HOSTED_VERIFIED, "hosted-verified")
        self.assertEqual(ALLOWED_RUN_TRACKS, {"local-public", "hosted-verified"})

    def test_http_adapter_posts_tasks_to_local_endpoint(self) -> None:
        answers = {
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
        received_task_ids: list[str] = []

        class MockHTTPAgent(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", "0"))
                task = json.loads(self.rfile.read(content_length).decode("utf-8"))
                received_task_ids.append(task["taskId"])
                response = json.dumps(answers[task["taskId"]], ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = HTTPServer(("127.0.0.1", 0), MockHTTPAgent)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            manifest = {
                "agentId": "mock-http-agent",
                "name": "Mock HTTP Agent",
                "version": "0.1.0",
                "adapter": {
                    "type": "http",
                    "endpoint": f"http://127.0.0.1:{server.server_port}/tasks",
                },
                "limits": {"timeoutSecondsPerTask": 5, "maxRunsPerTask": 1},
            }
            manifest_path = self.tmpdir / "mock_http.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            report = run_benchmark(
                manifest_path,
                PROJECT_ROOT / "examples/task_packs/mvp_v0.json",
                self.tmpdir / "http",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        task_pack = json.loads((PROJECT_ROOT / "examples/task_packs/mvp_v0.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["tasksPassed"], report["summary"]["tasksTotal"])
        self.assertGreater(report["summary"]["overall"], 90)
        self.assertTrue(all(attempt["verdict"] == "PASS" for attempt in report["attempts"]))
        self.assertEqual(received_task_ids, [task["taskId"] for task in task_pack["tasks"]])

    def test_leaderboard_ranks_good_agent_first(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_bad.json", task_pack, self.tmpdir / "runs/bad")
        run_benchmark(PROJECT_ROOT / "examples/manifests/mock_good.json", task_pack, self.tmpdir / "runs/good")

        rows = build_leaderboard(self.tmpdir / "runs", self.tmpdir / "leaderboard.json")

        self.assertEqual(rows[0]["agentId"], "mock-good-agent")
        self.assertEqual(rows[0]["rank"], 1)
        self.assertTrue((self.tmpdir / "leaderboard.json").exists())
        self.assertTrue((self.tmpdir / "leaderboard.md").exists())

    def test_beta_task_pack_has_launch_ready_category_coverage(self) -> None:
        task_pack = json.loads(
            (PROJECT_ROOT / "examples/task_packs/beta_v0_1.json").read_text(encoding="utf-8")
        )

        tasks = task_pack["tasks"]
        task_ids = [task["taskId"] for task in tasks]
        categories = {task["category"] for task in tasks}

        self.assertGreaterEqual(len(tasks), 20)
        self.assertEqual(len(task_ids), len(set(task_ids)))
        self.assertTrue(
            {"core", "tool-use", "safety", "memory-skills", "speed-cost"}.issubset(categories)
        )

    def test_good_agent_scores_higher_on_beta_task_pack(self) -> None:
        task_pack = PROJECT_ROOT / "examples/task_packs/beta_v0_1.json"
        good = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_good.json",
            task_pack,
            self.tmpdir / "beta-good",
        )
        bad = run_benchmark(
            PROJECT_ROOT / "examples/manifests/mock_bad.json",
            task_pack,
            self.tmpdir / "beta-bad",
        )

        self.assertGreater(good["summary"]["overall"], 85)
        self.assertGreaterEqual(good["summary"]["tasksPassed"], 19)
        self.assertLess(bad["summary"]["overall"], 35)
        self.assertGreater(good["summary"]["overall"], bad["summary"]["overall"])


if __name__ == "__main__":
    unittest.main()
