from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .adapter_contract import build_task_request, normalize_agent_response
from .evaluator import build_scoring_schema, evaluate_attempt, summarize_scores
from .schemas import RUN_TRACK_LOCAL_PUBLIC, load_json, stable_json_hash


def run_benchmark(manifest_path: str | Path, task_pack_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    task_pack_path = Path(task_pack_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(manifest_path)
    task_pack = load_json(task_pack_path)
    _validate_manifest(manifest)
    _validate_task_pack(task_pack)

    project_root = manifest_path.parent.parent.parent
    attempts = []
    for task in task_pack["tasks"]:
        output, elapsed = _invoke_agent(manifest, task, project_root)
        attempts.append(evaluate_attempt(task, output, elapsed))

    score_summary = summarize_scores(attempts)
    report = {
        "schemaVersion": "agentstack-benchmark.report.v0.1",
        "track": RUN_TRACK_LOCAL_PUBLIC,
        "agent": {
            "agentId": manifest["agentId"],
            "name": manifest["name"],
            "version": manifest["version"],
            "manifestHash": stable_json_hash(manifest),
        },
        "taskPack": {
            "taskPackId": task_pack["taskPackId"],
            "name": task_pack["name"],
            "version": task_pack["version"],
            "taskPackHash": stable_json_hash(task_pack),
        },
        "scoringSchema": build_scoring_schema(),
        "summary": score_summary,
        "attempts": attempts,
    }

    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown_report(report), encoding="utf-8")
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# AgentStack Benchmark Report — {report['agent']['name']}",
        "",
        f"Agent: `{report['agent']['agentId']}` v{report['agent']['version']}",
        f"Task pack: `{report['taskPack']['taskPackId']}` v{report['taskPack']['version']}",
        f"Track: `{report['track']}`",
        f"Scoring schema: `{report['scoringSchema']['schemaVersion']}`",
        f"Overall score: **{report['summary']['overall']}**",
        "",
        "## Scorecard",
    ]
    weights = report["scoringSchema"]["weights"]
    dimensions = report["summary"]["dimensions"]
    for key, weight in weights.items():
        lines.append(f"- {key} (weight {weight:.2f}): {dimensions[key]}")
    lines.extend(["", "## Task attempts"])
    for attempt in report["attempts"]:
        score_text = ", ".join(f"{key}={value}" for key, value in attempt["scores"].items())
        lines.append(
            f"- `{attempt['taskId']}` ({attempt['category']}): {attempt['verdict']} "
            f"in {attempt['elapsedSeconds']}s — scores: {score_text} — {attempt['answer']}"
        )
    lines.append("")
    return "\n".join(lines)


def _invoke_agent(manifest: dict[str, Any], task: dict[str, Any], project_root: Path) -> tuple[dict[str, Any], float]:
    adapter = manifest.get("adapter", {})
    adapter_type = adapter.get("type")
    if adapter_type == "cli":
        return _invoke_cli_agent(manifest, task, project_root)
    if adapter_type == "http":
        return _invoke_http_agent(manifest, task)
    raise ValueError("adapter.type must be one of: cli, http")


def _build_task_payload(
    task: dict[str, Any],
    default_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    return build_task_request(task, default_timeout_seconds=default_timeout_seconds)


def _invoke_cli_agent(manifest: dict[str, Any], task: dict[str, Any], project_root: Path) -> tuple[dict[str, Any], float]:
    adapter = manifest.get("adapter", {})
    command = adapter.get("command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError("adapter.command must be a string array")

    timeout = float(task.get("timeoutSeconds", manifest.get("limits", {}).get("timeoutSecondsPerTask", 10)))
    payload = json.dumps(_build_task_payload(task, timeout), ensure_ascii=False)

    started = time.monotonic()
    result = subprocess.run(
        command,
        input=payload,
        cwd=project_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    elapsed = time.monotonic() - started

    if result.returncode != 0:
        return {
            "answer": "",
            "toolTrace": [],
            "stderr": result.stderr[-2000:],
            "runtimeError": f"returncode={result.returncode}",
        }, elapsed

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {"answer": result.stdout, "toolTrace": []}
    if not isinstance(output, dict):
        output = {"answer": str(output), "toolTrace": []}
    return normalize_agent_response(output), elapsed


def _invoke_http_agent(manifest: dict[str, Any], task: dict[str, Any]) -> tuple[dict[str, Any], float]:
    adapter = manifest.get("adapter", {})
    endpoint = adapter.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("adapter.endpoint must be a non-empty string")
    _validate_local_http_endpoint(endpoint)

    timeout = float(task.get("timeoutSeconds", manifest.get("limits", {}).get("timeoutSecondsPerTask", 10)))
    payload = json.dumps(_build_task_payload(task, timeout), ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    started = time.monotonic()
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except (TimeoutError, error.URLError) as exc:
        elapsed = time.monotonic() - started
        return {
            "answer": "",
            "toolTrace": [],
            "runtimeError": f"http_error={exc}",
        }, elapsed
    elapsed = time.monotonic() - started

    try:
        output = json.loads(response_body)
    except json.JSONDecodeError:
        output = {
            "answer": "",
            "toolTrace": [],
            "runtimeError": "invalid_adapter_response: response body must be JSON object",
        }
    if not isinstance(output, dict):
        output = {
            "answer": "",
            "toolTrace": [],
            "runtimeError": "invalid_adapter_response: response body must be JSON object",
        }
    if "runtimeError" in output:
        return output, elapsed
    return normalize_agent_response(output), elapsed


def _validate_local_http_endpoint(endpoint: str) -> None:
    parsed = parse.urlparse(endpoint)
    if parsed.scheme != "http":
        raise ValueError("adapter.endpoint must use http for the local prototype")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("adapter.endpoint must target localhost/127.0.0.1 for the local prototype")


def _validate_manifest(manifest: dict[str, Any]) -> None:
    for key in ["agentId", "name", "version", "adapter"]:
        if key not in manifest:
            raise ValueError(f"Manifest missing required key: {key}")


def _validate_task_pack(task_pack: dict[str, Any]) -> None:
    for key in ["taskPackId", "name", "version", "tasks"]:
        if key not in task_pack:
            raise ValueError(f"Task pack missing required key: {key}")
    if not isinstance(task_pack["tasks"], list) or not task_pack["tasks"]:
        raise ValueError("Task pack must contain at least one task")
    for task in task_pack["tasks"]:
        for key in ["taskId", "prompt", "expected"]:
            if key not in task:
                raise ValueError(f"Task missing required key {key}: {task}")
