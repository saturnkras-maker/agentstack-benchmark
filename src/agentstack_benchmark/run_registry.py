from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import parse

from .schemas import canonicalize_report

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def collect_run_summaries(runs_dir: str | Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for report_path in sorted(Path(runs_dir).glob("*/report.json")):
        run_id = report_path.parent.name
        report = canonicalize_report(json.loads(report_path.read_text(encoding="utf-8")))
        summary = report["summary"]
        summaries.append(
            {
                "runId": run_id,
                "track": report["track"],
                "agentId": report["agent"]["agentId"],
                "agentName": report["agent"]["name"],
                "agentVersion": report["agent"]["version"],
                "taskPackId": report["taskPack"]["taskPackId"],
                "taskPackVersion": report["taskPack"]["version"],
                "overall": summary["overall"],
                "dimensions": summary["dimensions"],
                "tasksPassed": summary["tasksPassed"],
                "tasksTotal": summary["tasksTotal"],
                "reportEndpoint": f"/api/v1/runs/{parse.quote(run_id, safe='')}/report",
            }
        )
    return summaries


def load_run_report(runs_dir: str | Path, run_id: str) -> dict[str, Any] | None:
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise ValueError("runId must be a safe path segment")
    report_path = Path(runs_dir) / run_id / "report.json"
    if not report_path.exists():
        return None
    return canonicalize_report(json.loads(report_path.read_text(encoding="utf-8")))
