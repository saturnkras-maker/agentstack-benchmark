from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .offline_demo import DEFAULT_TASK_PACK_PATH, RESPONSE_SCHEMA_VERSION
from .runner import run_benchmark

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_OPENAI_COMPATIBLE_BASE_URLS = (
    "http://127.0.0.1:8080/v1",
    "http://127.0.0.1:8000/v1",
    "http://127.0.0.1:1234/v1",
)
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


@dataclass
class LocalModelBackend:
    available: bool
    provider: str
    base_url: str | None = None
    model: str | None = None
    reason: str | None = None
    internetRequired: bool = False
    apiKeysRequired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_loopback_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "") in LOOPBACK_HOSTS


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 1.5,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback-only callers
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def probe_openai_compatible_backend(
    base_url: str,
    *,
    model: str | None = None,
    timeout: float = 1.5,
) -> LocalModelBackend:
    base_url = base_url.rstrip("/")
    if not _is_loopback_url(base_url):
        return LocalModelBackend(
            available=False,
            provider="openai-compatible",
            base_url=base_url,
            model=model,
            reason="local-model-endpoint-must-be-loopback",
        )
    try:
        body = _request_json(f"{base_url}/models", timeout=timeout)
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return LocalModelBackend(
            available=False,
            provider="openai-compatible",
            base_url=base_url,
            model=model,
            reason=f"local-model-unreachable:{exc.__class__.__name__}",
        )
    models = body.get("data") or []
    discovered_model = model
    if not discovered_model and models and isinstance(models[0], dict):
        discovered_model = str(models[0].get("id") or "") or None
    if not discovered_model:
        return LocalModelBackend(
            available=False,
            provider="openai-compatible",
            base_url=base_url,
            reason="local-model-list-empty",
        )
    return LocalModelBackend(
        available=True,
        provider="openai-compatible",
        base_url=base_url,
        model=discovered_model,
    )


def probe_ollama_backend(
    host: str = DEFAULT_OLLAMA_HOST,
    *,
    model: str | None = None,
    timeout: float = 1.5,
) -> LocalModelBackend:
    host = host.rstrip("/")
    if not _is_loopback_url(host):
        return LocalModelBackend(
            available=False,
            provider="ollama",
            base_url=host,
            model=model,
            reason="local-model-endpoint-must-be-loopback",
        )
    try:
        body = _request_json(f"{host}/api/tags", timeout=timeout)
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return LocalModelBackend(
            available=False,
            provider="ollama",
            base_url=host,
            model=model,
            reason=f"local-model-unreachable:{exc.__class__.__name__}",
        )
    models = body.get("models") or []
    discovered_model = model
    if not discovered_model and models and isinstance(models[0], dict):
        discovered_model = str(models[0].get("name") or models[0].get("model") or "") or None
    if not discovered_model:
        return LocalModelBackend(
            available=False,
            provider="ollama",
            base_url=host,
            reason="local-model-list-empty",
        )
    return LocalModelBackend(available=True, provider="ollama", base_url=host, model=discovered_model)


def discover_local_model_backend(
    *,
    base_url: str | None = None,
    model: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 1.5,
) -> LocalModelBackend:
    env = env or {}
    explicit_base_url = base_url or env.get("AGENTSTACK_LOCAL_MODEL_BASE_URL")
    explicit_model = model or env.get("AGENTSTACK_LOCAL_MODEL_NAME")
    if explicit_base_url:
        if "/api" in urllib.parse.urlparse(explicit_base_url).path or "11434" in explicit_base_url:
            return probe_ollama_backend(explicit_base_url, model=explicit_model, timeout=timeout)
        return probe_openai_compatible_backend(
            explicit_base_url,
            model=explicit_model,
            timeout=timeout,
        )

    ollama_host = env.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    ollama = probe_ollama_backend(ollama_host, model=explicit_model, timeout=timeout)
    if ollama.available:
        return ollama

    for candidate in DEFAULT_OPENAI_COMPATIBLE_BASE_URLS:
        backend = probe_openai_compatible_backend(candidate, model=explicit_model, timeout=timeout)
        if backend.available:
            return backend

    return LocalModelBackend(
        available=False,
        provider="none",
        reason="no-loopback-local-model-backend-detected",
    )


def _build_task_prompt(task: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are a local AI agent adapter being evaluated by AgentStack Benchmark.",
            "Return only the final answer text for the task.",
            f"taskId: {task.get('taskId', '')}",
            f"title: {task.get('title', '')}",
            f"prompt: {task.get('prompt', '')}",
        ]
    )


def call_local_model(task: dict[str, Any], backend: LocalModelBackend, timeout: float = 15.0) -> str:
    if not backend.available or not backend.base_url or not backend.model:
        raise RuntimeError("Local model backend is not available")
    prompt = _build_task_prompt(task)
    if backend.provider == "ollama":
        body = _request_json(
            f"{backend.base_url.rstrip('/')}/api/chat",
            method="POST",
            body={
                "model": backend.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a concise local benchmark agent."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=timeout,
        )
        message = body.get("message") or {}
        return str(message.get("content") or body.get("response") or "")
    body = _request_json(
        f"{backend.base_url.rstrip('/')}/chat/completions",
        method="POST",
        body={
            "model": backend.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are a concise local benchmark agent."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=timeout,
    )
    choices = body.get("choices") or []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        return str(message.get("content") or choices[0].get("text") or "")
    return ""


@dataclass
class LocalModelAgentServer:
    server: ThreadingHTTPServer
    thread: threading.Thread
    endpoint: str
    backend: LocalModelBackend

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _build_local_model_handler(backend: LocalModelBackend) -> type[BaseHTTPRequestHandler]:
    class LocalModelAgentHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/tasks":
                self.send_error(404)
                return
            content_length = int(self.headers.get("Content-Length", "0"))
            task = json.loads(self.rfile.read(content_length).decode("utf-8"))
            answer = call_local_model(task, backend)
            body = {
                "schemaVersion": RESPONSE_SCHEMA_VERSION,
                "answer": answer,
                "toolTrace": [f"local_model:{backend.provider}"],
            }
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return LocalModelAgentHandler


def start_local_model_agent(
    backend: LocalModelBackend,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> LocalModelAgentServer:
    if not backend.available:
        raise RuntimeError("Cannot start local model agent without an available backend")
    server = ThreadingHTTPServer((host, port), _build_local_model_handler(backend))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://{host}:{server.server_port}/tasks"
    return LocalModelAgentServer(server=server, thread=thread, endpoint=endpoint, backend=backend)


def build_local_model_manifest(endpoint: str, backend: LocalModelBackend) -> dict[str, Any]:
    return {
        "agentId": "local-model-agent",
        "name": "Local Model Agent",
        "version": "0.1.0",
        "adapter": {"type": "http", "endpoint": endpoint},
        "model": {
            "provider": backend.provider,
            "name": backend.model or "unknown-local-model",
        },
        "capabilities": {
            "browser": False,
            "terminal": False,
            "files": False,
            "memory": False,
            "skills": False,
            "mcp": False,
        },
        "limits": {"timeoutSecondsPerTask": 30, "maxRunsPerTask": 1},
    }


def write_local_model_manifest(
    endpoint: str,
    backend: LocalModelBackend,
    path: str | Path,
) -> dict[str, Any]:
    manifest = build_local_model_manifest(endpoint, backend)
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_local_model_demo_once(
    *,
    backend: LocalModelBackend,
    runs_dir: str | Path,
    run_id: str = "local-model-demo-run",
    host: str = "127.0.0.1",
    agent_port: int = 8765,
    task_pack_path: str | Path = DEFAULT_TASK_PACK_PATH,
) -> dict[str, Any]:
    runs_root = Path(runs_dir)
    agent = start_local_model_agent(backend, host=host, port=agent_port)
    try:
        manifest_path = runs_root / "_submitted_manifests" / f"{run_id}.json"
        write_local_model_manifest(agent.endpoint, backend, manifest_path)
        out_dir = runs_root / run_id
        report = run_benchmark(manifest_path, task_pack_path, out_dir)
        return {
            "mode": "local-model-demo",
            "internetRequired": False,
            "apiKeysRequired": False,
            "localModelProvider": backend.provider,
            "localModelBaseUrl": backend.base_url,
            "localModelName": backend.model,
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
