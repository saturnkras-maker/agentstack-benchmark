from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
from urllib import request

from .offline_demo import run_offline_demo_once
from .security import SecurityConfig
from .server import make_server

LOCAL_MVP_VERIFICATION_SCHEMA_VERSION = "agentstack-benchmark.local-mvp-verification.v0.1"


def verify_local_mvp(
    repo_root: str | Path = ".",
    out_dir: str | Path = "artifacts/local-mvp-verification",
    host: str = "127.0.0.1",
    ui_port: int = 0,
    agent_port: int = 0,
    run_id: str = "verify-offline-demo-run",
) -> dict[str, Any]:
    """Run the local MVP proof loop and write a compact proof bundle.

    This is intentionally local-only: it starts a deterministic loopback demo agent,
    creates one local-public report, serves that report from the stdlib preview server,
    fetches the browser/API surfaces, and writes proof artifacts. It does not perform
    deploy, billing, hosted-runner, API-key, or external-network actions.
    """

    repo_root = Path(repo_root).resolve()
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    runs_dir = out_path / "runs"

    demo_summary = run_offline_demo_once(
        runs_dir=runs_dir,
        run_id=run_id,
        host=host,
        agent_port=agent_port,
        task_pack_path=repo_root / "examples/task_packs/mvp_v0.json",
    )

    server = make_server(
        host,
        ui_port,
        runs_dir,
        security_config=SecurityConfig.disabled(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{host}:{server.server_port}"
    try:
        endpoint_checks = [
            _check_endpoint(base_url, "/api/v1/healthz", "application/json", ["ok", "free-beta"]),
            _check_endpoint(base_url, "/cockpit", "text/html", ["Local MVP Cockpit", run_id]),
            _check_endpoint(base_url, "/api/v1/cockpit", "application/json", ["ready", run_id]),
            _check_endpoint(base_url, "/run", "text/html", ["Run benchmark", "No API keys"]),
            _check_endpoint(base_url, "/leaderboard", "text/html", ["Offline Demo Agent", "local-public"]),
            _check_endpoint(base_url, f"/runs/{run_id}", "text/html", ["Offline Demo Agent", "98.88"]),
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    status = "pass" if _run_summary_ok(demo_summary) and all(item["ok"] for item in endpoint_checks) else "fail"
    report = {
        "schemaVersion": LOCAL_MVP_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "baseUrl": base_url,
        "run": {
            "runId": demo_summary["runId"],
            "overall": demo_summary["overall"],
            "tasksPassed": demo_summary["tasksPassed"],
            "tasksTotal": demo_summary["tasksTotal"],
            "reportPath": _relative_or_string(repo_root, demo_summary["reportPath"]),
            "markdownPath": _relative_or_string(repo_root, demo_summary["markdownPath"]),
        },
        "endpointChecks": endpoint_checks,
        "internetRequired": False,
        "apiKeysRequired": False,
        "hostedRunnerIncluded": False,
        "billingCheckoutConnected": False,
        "externalActionsPerformed": False,
        "proofFiles": {
            "json": str(out_path / "local_mvp_verification.json"),
            "markdown": str(out_path / "local_mvp_verification.md"),
        },
    }
    (out_path / "local_mvp_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_path / "local_mvp_verification.md").write_text(
        render_local_mvp_verification_markdown(report),
        encoding="utf-8",
    )
    return report


def render_local_mvp_verification_markdown(report: dict[str, Any]) -> str:
    status = "PASS" if report["status"] == "pass" else "FAIL"
    lines = [
        "# AgentStack Benchmark local MVP verification",
        "",
        f"Status: **{status}**",
        "",
        "## Run proof",
        "",
        f"- runId: `{report['run']['runId']}`",
        f"- overall: `{report['run']['overall']}`",
        f"- tasks: `{report['run']['tasksPassed']}/{report['run']['tasksTotal']}`",
        "",
        "## Endpoint proof",
        "",
    ]
    for check in report["endpointChecks"]:
        verdict = "PASS" if check["ok"] else "FAIL"
        lines.append(f"- {verdict} `{check['path']}` HTTP {check['status']} {check['contentType']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- No internet required.",
            "- No API keys required.",
            "- No hosted runner included.",
            "- No billing checkout connected.",
            "- No external actions performed.",
            "",
        ]
    )
    return "\n".join(lines)


def _check_endpoint(base_url: str, path: str, expected_content_type: str, markers: list[str]) -> dict[str, Any]:
    url = f"{base_url}{path}"
    try:
        with request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
            content_type = response.headers.get_content_type()
    except Exception as exc:  # pragma: no cover - exercised as failed proof data
        return {
            "path": path,
            "status": 0,
            "contentType": "",
            "ok": False,
            "markers": {marker: False for marker in markers},
            "error": str(exc),
        }
    marker_checks = {marker: marker in body for marker in markers}
    return {
        "path": path,
        "status": status,
        "contentType": content_type,
        "ok": status == 200 and content_type == expected_content_type and all(marker_checks.values()),
        "markers": marker_checks,
    }


def _run_summary_ok(summary: dict[str, Any]) -> bool:
    return summary.get("overall") == 98.88 and summary.get("tasksPassed") == 5 and summary.get("tasksTotal") == 5


def _relative_or_string(repo_root: Path, value: str) -> str:
    path = Path(value)
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path)
