from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_leaderboard(runs_dir: str | Path, out_path: str | Path) -> list[dict[str, Any]]:
    runs_dir = Path(runs_dir)
    out_path = Path(out_path)
    rows: list[dict[str, Any]] = []
    for report_path in sorted(runs_dir.glob("*/report.json")):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "rank": 0,
                "agentId": report["agent"]["agentId"],
                "agentName": report["agent"]["name"],
                "agentVersion": report["agent"]["version"],
                "taskPackId": report["taskPack"]["taskPackId"],
                "overall": report["summary"]["overall"],
                "dimensions": report["summary"]["dimensions"],
                "tasksPassed": report["summary"]["tasksPassed"],
                "tasksTotal": report["summary"]["tasksTotal"],
                "reportPath": str(report_path),
            }
        )
    rows.sort(key=lambda item: (-float(item["overall"]), item["agentId"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = out_path.with_suffix(".md")
    md_path.write_text(render_leaderboard_markdown(rows), encoding="utf-8")
    return rows


def render_leaderboard_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# AgentStack Benchmark Leaderboard", ""]
    if not rows:
        lines.append("No runs found.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.append(
            f"{row['rank']}. **{row['agentName']}** (`{row['agentId']}`) — "
            f"overall **{row['overall']}**, passed {row['tasksPassed']}/{row['tasksTotal']}"
        )
        dims = row["dimensions"]
        lines.append(
            f"   - quality {dims['quality']} · reliability {dims['reliability']} · "
            f"safety {dims['safety']} · speed {dims['speed']} · toolUse {dims['toolUse']}"
        )
        lines.append(f"   - report: `{row['reportPath']}`")
    lines.append("")
    return "\n".join(lines)
