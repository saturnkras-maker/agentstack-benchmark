from __future__ import annotations

import platform
import socket
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .local_model import LocalModelBackend, discover_local_model_backend


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) != 0


def _skipped_local_model_status() -> dict[str, Any]:
    return asdict(
        LocalModelBackend(
            available=False,
            provider="none",
            reason="probe-skipped",
        )
    )


def build_first_run_doctor_report(
    *,
    repo_root: str | Path = ".",
    host: str = "127.0.0.1",
    ui_port: int = 8088,
    agent_port: int = 8765,
    probe_local_model: bool = True,
    local_model_base_url: str | None = None,
    local_model_name: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    local_model = (
        discover_local_model_backend(
            base_url=local_model_base_url,
            model=local_model_name,
            env=env,
        ).to_dict()
        if probe_local_model
        else _skipped_local_model_status()
    )
    recommended_mode = "auto-local-model" if local_model["available"] else "offline"
    base_url = f"http://{host}:{ui_port}"
    agent_endpoint = f"http://{host}:{agent_port}/tasks"
    offline_demo_command = (
        "PYTHONPATH=src python3 -m agentstack_benchmark.cli demo-local "
        f"--host {host} --agent-port {agent_port} --ui-port {ui_port}"
    )
    auto_model_command = offline_demo_command + " --agent-mode auto-local-model"
    return {
        "status": "ready",
        "internetRequired": False,
        "apiKeysRequired": False,
        "doesNotStartServers": True,
        "recommendedMode": recommended_mode,
        "python": {
            "version": platform.python_version(),
            "executableName": Path(sys.executable).name,
        },
        "paths": {
            "repoRootExists": repo_root.exists(),
            "srcExists": (repo_root / "src").exists(),
            "offlineDemoDocExists": (repo_root / "docs/offline-local-mvp-demo.md").exists(),
            "localModelDocExists": (repo_root / "docs/local-model-adapter-v0.1.md").exists(),
        },
        "ports": {
            "ui": {"host": host, "port": ui_port, "free": _port_is_free(host, ui_port)},
            "agent": {"host": host, "port": agent_port, "free": _port_is_free(host, agent_port)},
        },
        "localModel": local_model,
        "urls": {
            "ui": f"{base_url}/",
            "runForm": f"{base_url}/run",
            "initialReport": f"{base_url}/runs/offline-demo-run",
            "leaderboard": f"{base_url}/leaderboard",
            "agentEndpoint": agent_endpoint,
        },
        "commands": {
            "offlineDemo": offline_demo_command,
            "autoLocalModel": auto_model_command,
            "localModelCheck": "PYTHONPATH=src python3 -m agentstack_benchmark.cli local-model-check",
            "smokeOnce": offline_demo_command + " --once",
        },
        "nextStep": "run offlineDemo unless localModel.available is true; then run autoLocalModel",
    }
