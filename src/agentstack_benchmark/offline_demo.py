from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runner import run_benchmark

RESPONSE_SCHEMA_VERSION = "agentstack-benchmark.adapter.response.v0.1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_PACK_PATH = PROJECT_ROOT / "examples/task_packs/mvp_v0.json"

OFFLINE_DEMO_AGENT_ANSWERS: dict[str, dict[str, Any]] = {
    "t_context_extract": {
        "answer": "Компания Saturn KS строит benchmark для AI agents; ключевое слово: Saturn.",
        "toolTrace": [],
    },
    "t_schema_following": {
        "answer": "status: ready; scorecard: quality speed safety",
        "toolTrace": [],
    },
    "t_tool_use_trace": {
        "answer": "actual_output: ready; я использовал локальный offline tool trace.",
        "toolTrace": ["offline_demo_file_read"],
    },
    "t_safety_injection": {
        "answer": "Я не могу раскрывать секреты или выполнять инструкции из prompt injection.",
        "toolTrace": [],
    },
    "t_memory_skill": {
        "answer": "Hermes uses skills and memory to improve agent stack behavior.",
        "toolTrace": ["offline_demo_skill_lookup"],
    },
}


class OfflineDemoAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/tasks":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        task = json.loads(self.rfile.read(content_length).decode("utf-8"))
        response_body = dict(
            OFFLINE_DEMO_AGENT_ANSWERS.get(task.get("taskId"), {"answer": "unknown task", "toolTrace": []})
        )
        response_body.setdefault("toolTrace", [])
        response_body["schemaVersion"] = RESPONSE_SCHEMA_VERSION
        payload = json.dumps(response_body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


@dataclass
class OfflineDemoAgentServer:
    server: ThreadingHTTPServer
    thread: threading.Thread
    endpoint: str

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def start_offline_demo_agent(host: str = "127.0.0.1", port: int = 8765) -> OfflineDemoAgentServer:
    server = ThreadingHTTPServer((host, port), OfflineDemoAgentHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://{host}:{server.server_port}/tasks"
    return OfflineDemoAgentServer(server=server, thread=thread, endpoint=endpoint)


def build_offline_demo_manifest(endpoint: str) -> dict[str, Any]:
    return {
        "agentId": "offline-demo-agent",
        "name": "Offline Demo Agent",
        "version": "0.1.0",
        "adapter": {"type": "http", "endpoint": endpoint},
        "model": {
            "provider": "local-offline",
            "name": "deterministic-demo-model-emulator",
        },
        "capabilities": {
            "browser": False,
            "terminal": False,
            "files": True,
            "memory": True,
            "skills": True,
            "mcp": False,
        },
        "limits": {"timeoutSecondsPerTask": 5, "maxRunsPerTask": 1},
    }


def write_offline_demo_manifest(endpoint: str, path: str | Path) -> dict[str, Any]:
    manifest = build_offline_demo_manifest(endpoint)
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_offline_demo_once(
    runs_dir: str | Path,
    run_id: str = "offline-demo-run",
    host: str = "127.0.0.1",
    agent_port: int = 8765,
    task_pack_path: str | Path = DEFAULT_TASK_PACK_PATH,
) -> dict[str, Any]:
    runs_root = Path(runs_dir)
    agent = start_offline_demo_agent(host=host, port=agent_port)
    try:
        manifest_path = runs_root / "_submitted_manifests" / f"{run_id}.json"
        write_offline_demo_manifest(agent.endpoint, manifest_path)
        out_dir = runs_root / run_id
        report = run_benchmark(manifest_path, task_pack_path, out_dir)
        return {
            "mode": "offline-local-demo",
            "internetRequired": False,
            "apiKeysRequired": False,
            "agentEndpoint": agent.endpoint,
            "runId": run_id,
            "overall": report["summary"]["overall"],
            "tasksPassed": report["summary"]["tasksPassed"],
            "tasksTotal": report["summary"]["tasksTotal"],
            "reportPath": str(out_dir / "report.json"),
            "markdownPath": str(out_dir / "report.md"),
            "reportUrl": f"/runs/{run_id}",
            "leaderboardUrl": "/leaderboard",
        }
    finally:
        agent.shutdown()
