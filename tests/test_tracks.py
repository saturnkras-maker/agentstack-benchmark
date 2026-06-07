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


class TrackCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="agentstack-track-capability-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_track_capabilities_define_verified_boundary(self) -> None:
        from agentstack_benchmark.tracks import build_track_capabilities

        capabilities = build_track_capabilities()

        self.assertEqual(
            capabilities["schemaVersion"],
            "agentstack-benchmark.track-capabilities.v0.1",
        )
        self.assertEqual(capabilities["defaultTrack"], "local-public")
        by_track = {track["track"]: track for track in capabilities["tracks"]}
        self.assertEqual(set(by_track), {"local-public", "hosted-verified"})

        local_public = by_track["local-public"]
        self.assertEqual(local_public["status"], "active")
        self.assertEqual(local_public["assignmentAuthority"], "local-runner")
        self.assertTrue(local_public["localRunnerCanAssign"])
        self.assertFalse(local_public["hiddenTasksAllowed"])
        self.assertEqual(local_public["taskVisibility"], ["public"])

        hosted_verified = by_track["hosted-verified"]
        self.assertEqual(hosted_verified["status"], "reserved")
        self.assertEqual(hosted_verified["assignmentAuthority"], "server-side-hosted-runner")
        self.assertFalse(hosted_verified["localRunnerCanAssign"])
        self.assertTrue(hosted_verified["hiddenTasksAllowed"])
        self.assertEqual(hosted_verified["taskVisibility"], ["public", "hidden"])
        self.assertTrue(hosted_verified["requiresHostedInfra"])

        policy = capabilities["localRunnerPolicy"]
        self.assertEqual(policy["assignedTrack"], "local-public")
        self.assertTrue(policy["rejectsHiddenTasks"])
        self.assertFalse(policy["canAssignHostedVerified"])

    def test_local_runner_rejects_hidden_tasks_in_public_task_pack(self) -> None:
        hidden_markers = [
            {"visibility": "hidden"},
            {"hidden": True},
            {"requiresTrack": "hosted-verified"},
        ]
        for index, marker in enumerate(hidden_markers, start=1):
            with self.subTest(marker=marker):
                hidden_pack = {
                    "taskPackId": f"hidden-local-rejected-{index}",
                    "name": "Hidden Local Rejected",
                    "version": "0.1.0",
                    "tasks": [
                        {
                            "taskId": f"hidden_task_{index}",
                            "category": "core",
                            "prompt": "This task must not run in local-public mode.",
                            "expected": {"type": "contains", "value": "never"},
                            **marker,
                        }
                    ],
                }
                task_pack_path = self.tmpdir / f"hidden_pack_{index}.json"
                task_pack_path.write_text(json.dumps(hidden_pack), encoding="utf-8")

                with self.assertRaisesRegex(ValueError, "hidden tasks require hosted-verified"):
                    run_benchmark(
                        PROJECT_ROOT / "examples/manifests/mock_good.json",
                        task_pack_path,
                        self.tmpdir / f"hidden-run-{index}",
                    )
                self.assertFalse((self.tmpdir / f"hidden-run-{index}/report.json").exists())

    def test_track_capabilities_are_exposed_from_local_api(self) -> None:
        server = make_server("127.0.0.1", 0, self.tmpdir / "runs")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)

        url = f"http://127.0.0.1:{server.server_port}/api/v1/tracks"
        with request.urlopen(url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(body["service"], "agentstack-benchmark")
        self.assertEqual(body["pricingMode"], "free-beta")
        self.assertEqual(body["trackCapabilities"]["defaultTrack"], "local-public")
        hosted = {
            track["track"]: track for track in body["trackCapabilities"]["tracks"]
        }["hosted-verified"]
        self.assertFalse(hosted["localRunnerCanAssign"])
        self.assertTrue(hosted["hiddenTasksAllowed"])


if __name__ == "__main__":
    unittest.main()
