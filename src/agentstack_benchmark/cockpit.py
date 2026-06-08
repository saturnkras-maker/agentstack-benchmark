from __future__ import annotations

from pathlib import Path
from typing import Any

from .doctor import build_first_run_doctor_report
from .run_registry import collect_run_summaries
from .schemas import RUN_TRACK_LOCAL_PUBLIC

LOCAL_MVP_COCKPIT_SCHEMA_VERSION = "agentstack-benchmark.local-mvp-cockpit.v0.1"


def _rank_runs(runs_dir: str | Path) -> list[dict[str, Any]]:
    rows = sorted(
        collect_run_summaries(runs_dir),
        key=lambda item: (-float(item["overall"]), str(item["agentId"]), str(item["runId"])),
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def build_local_mvp_cockpit_report(
    *,
    runs_dir: str | Path,
    repo_root: str | Path = ".",
    host: str = "127.0.0.1",
    ui_port: int = 8088,
    agent_port: int = 8765,
    probe_local_model: bool = False,
    local_model_base_url: str | None = None,
    local_model_name: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the local MVP cockpit summary without exposing local file paths.

    The cockpit is a first-run orientation surface: it combines readiness, exact
    local commands, important browser URLs, run summaries, and safe launch
    boundaries into one JSON shape. It intentionally defaults to a skipped local
    model probe so opening the web page never performs unexpected network work.
    """

    doctor = build_first_run_doctor_report(
        repo_root=repo_root,
        host=host,
        ui_port=ui_port,
        agent_port=agent_port,
        probe_local_model=probe_local_model,
        local_model_base_url=local_model_base_url,
        local_model_name=local_model_name,
        env=env,
    )
    rows = _rank_runs(runs_dir)
    leader = rows[0] if rows else None
    base_url = f"http://{host}:{ui_port}"
    recommended_next_action = (
        "run-auto-local-model" if doctor["localModel"].get("available") else "run-offline-demo"
    )
    return {
        "schemaVersion": LOCAL_MVP_COCKPIT_SCHEMA_VERSION,
        "status": "ready",
        "track": RUN_TRACK_LOCAL_PUBLIC,
        "pricingMode": "free-beta",
        "internetRequired": False,
        "apiKeysRequired": False,
        "billingCheckoutConnected": False,
        "hostedVerifiedStatus": "reserved",
        "doesNotStartServers": True,
        "recommendedNextAction": recommended_next_action,
        "doctor": doctor,
        "localModel": doctor["localModel"],
        "urls": {
            "cockpit": f"{base_url}/cockpit",
            "ui": f"{base_url}/",
            "runForm": f"{base_url}/run",
            "leaderboard": f"{base_url}/leaderboard",
            "initialReport": f"{base_url}/runs/offline-demo-run",
            "agentEndpoint": doctor["urls"]["agentEndpoint"],
            "cockpitApi": f"{base_url}/api/v1/cockpit",
        },
        "commands": {
            "doctor": "make doctor",
            "cockpit": "make cockpit",
            "offlineDemo": "make demo-local",
            "offlineSmoke": "make demo-local-once",
            "localModelCheck": "make local-model-check",
            "autoLocalModel": "make demo-local-auto",
            "autoLocalModelSmoke": "make demo-local-auto-once",
            "explicitPythonDoctor": doctor["commands"]["localModelCheck"].replace(
                "local-model-check", "doctor"
            ),
            "explicitPythonOfflineDemo": doctor["commands"]["offlineDemo"],
        },
        "runs": {
            "count": len(rows),
            "leader": leader,
            "recent": rows[:5],
        },
        "docs": [
            "README.md",
            "docs/local-mvp-cockpit-v0.1.md",
            "docs/offline-local-mvp-demo.md",
            "docs/first-run-doctor-v0.1.md",
            "docs/local-model-adapter-v0.1.md",
        ],
        "safety": {
            "externalDeployPerformed": False,
            "billingEnabled": False,
            "paymentConfigured": False,
            "credentialMaterialEmbedded": False,
            "remoteExecutionEnabled": False,
        },
        "nextSteps": [
            "Run make doctor to confirm local readiness.",
            "Run make demo-local to start the offline demo agent and browser UI.",
            "Open /cockpit for the guided local control surface.",
            "Use /run with http://127.0.0.1:8765/tasks to generate a visual report.",
        ],
    }
