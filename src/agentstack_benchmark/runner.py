from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .evaluator import evaluate_attempt, summarize_scores
from .schemas import load_json, stable_json_hash


def run_benchmark(manifest_path: str | Path, task_pack_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    task_pack_path = Path(task_pack_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(manifest_path)
    task_pack = load_json(task_pack_path)
    _validate_manifest(manifest)
    _validate_task_pack(task_pack)

    attempts = []
    for task in task_pack["tasks"]:
        output, elapsed = _invoke_cli_agent(manifest, task, manifest_path.parent.parent.parent)
        attempts.append(evaluate_attempt(task, output, elapsed))

    score_summary = summarize_scores(attempts)
    report = {
        "schemaVersion": "agentstack-benchmark.report.v0.1",
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
        f"Overall score: **{report['summary']['overall']}**",
        "",
        "## Dimensions",
    ]
    for key, value in sorted(report["summary"]["dimensions"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Task attempts"])
    for attempt in report["attempts"]:
        lines.append(
            f"- `{attempt['taskId']}` ({attempt['category']}): {attempt['verdict']} "
            f"in {attempt['elapsedSeconds']}s — {attempt['answer']}"
        )
    lines.append("")
    return "\n".join(lines)


def _invoke_cli_agent(manifest: dict[str, Any], task: dict[str, Any], project_root: Path) -> tuple[dict[str, Any], float]:
    adapter = manifest.get("adapter", {})
    if adapter.get("type") != "cli":
        raise ValueError("Only cli adapter is supported in prototype v0.1")
    command = adapter.get("command")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise ValueError("adapter.command must be a string array")

    timeout = float(task.get("timeoutSeconds", manifest.get("limits", {}).get("timeoutSecondsPerTask", 10)))
    payload = json.dumps(
        {
            "taskId": task["taskId"],
            "category": task.get("category", "core"),
            "prompt": task["prompt"],
            "context": task.get("context", {}),
        },
        ensure_ascii=False,
    )

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
    return output, elapsed


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
