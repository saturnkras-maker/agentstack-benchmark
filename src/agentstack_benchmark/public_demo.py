from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from .leaderboard import build_leaderboard
from .offline_demo import run_offline_demo_once
from .pilots import DEFAULT_PILOT_REGISTRY_PATH, load_pilot_registry, run_local_pilots

PUBLIC_DEMO_SCHEMA_VERSION = "agentstack-benchmark.public-demo.v0.1"


def build_public_demo_site(
    repo_root: str | Path = ".",
    out_dir: str | Path = "site/demo",
) -> dict[str, Any]:
    """Build static, committed demo pages for the public launch surface.

    The generated files are static local-public samples: no hosted runner, no external
    model call, no billing checkout, and no private credentials. They are meant to
    let a visitor see the report/leaderboard shape before cloning the repo.
    """

    repo_root = Path(repo_root).resolve()
    out_path = Path(out_dir)
    generated_dir = out_path / "_generated"
    if generated_dir.exists():
        shutil.rmtree(generated_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    sample_run_id = "public-demo-offline-run"
    sample_summary = run_offline_demo_once(
        runs_dir=generated_dir / "runs" / "sample",
        run_id=sample_run_id,
        host="127.0.0.1",
        agent_port=0,
        task_pack_path=repo_root / "examples/task_packs/mvp_v0.json",
    )
    sample_report_path = generated_dir / "runs" / "sample" / sample_run_id / "report.json"
    sample_report = json.loads(sample_report_path.read_text(encoding="utf-8"))

    pilot_runs_dir = generated_dir / "runs" / "pilots"
    registry_path = repo_root / DEFAULT_PILOT_REGISTRY_PATH
    registry = load_pilot_registry(registry_path)
    pilot_reports = run_local_pilots(
        registry_path=registry_path,
        task_pack_path=repo_root / "examples/task_packs/mvp_v0.json",
        out_dir=pilot_runs_dir,
    )
    leaderboard_path = generated_dir / "pilot-leaderboard.json"
    raw_rows = build_leaderboard(pilot_runs_dir, leaderboard_path)
    leaderboard_rows = [_sanitize_leaderboard_row(row) for row in raw_rows]

    public_demo_manifest = {
        "schemaVersion": PUBLIC_DEMO_SCHEMA_VERSION,
        "status": "static-local-public-sample-ready",
        "track": "local-public",
        "sampleRun": {
            "runId": sample_run_id,
            "agentId": sample_report["agent"]["agentId"],
            "agentName": sample_report["agent"]["name"],
            "overall": sample_report["summary"]["overall"],
            "tasksPassed": sample_report["summary"]["tasksPassed"],
            "tasksTotal": sample_report["summary"]["tasksTotal"],
        },
        "pilotLeaderboard": {
            "entries": len(leaderboard_rows),
            "registry": "examples/pilots/local_public_v0_1.json",
            "mode": registry["pilots"][0]["localPilotMode"],
        },
        "hostedRunnerIncluded": False,
        "billingCheckoutConnected": False,
        "apiKeysRequired": False,
        "internetRequiredForDemo": False,
        "files": {
            "index": "site/demo/index.html",
            "report": "site/demo/report.html",
            "leaderboard": "site/demo/leaderboard.html",
            "reportJson": "site/demo/report.json",
            "leaderboardJson": "site/demo/leaderboard.json",
        },
    }

    (out_path / "report.json").write_text(
        json.dumps(_public_report(sample_report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_path / "leaderboard.json").write_text(
        json.dumps(leaderboard_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_path / "public-demo.json").write_text(
        json.dumps(public_demo_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_path / "index.html").write_text(
        _render_demo_index(public_demo_manifest),
        encoding="utf-8",
    )
    (out_path / "report.html").write_text(
        _render_static_report(sample_report),
        encoding="utf-8",
    )
    (out_path / "leaderboard.html").write_text(
        _render_static_leaderboard(leaderboard_rows, pilot_reports),
        encoding="utf-8",
    )
    shutil.rmtree(generated_dir)
    return public_demo_manifest


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": report["schemaVersion"],
        "track": report["track"],
        "agent": report["agent"],
        "taskPack": report["taskPack"],
        "scoringSchema": report["scoringSchema"],
        "summary": report["summary"],
        "reproducibility": report["reproducibility"],
        "attempts": report["attempts"],
        "sampleBoundary": {
            "staticLocalPublicSample": True,
            "hostedRunnerIncluded": False,
            "billingCheckoutConnected": False,
            "apiKeysRequired": False,
        },
    }


def _sanitize_leaderboard_row(row: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(row)
    sanitized["reportPath"] = f"site/demo/pilot-reports/{row['agentId']}/report.json"
    return sanitized


def _render_demo_index(manifest: dict[str, Any]) -> str:
    sample = manifest["sampleRun"]
    return _page(
        "AgentStack Benchmark — static demo",
        f"""
        <section class="hero">
          <p class="eyebrow">Static local-public sample</p>
          <h1>See the report shape before running locally.</h1>
          <p>This static public demo is generated from deterministic local artifacts. It is not a hosted runner and it does not use API keys, external models, or billing.</p>
          <div class="actions">
            <a class="button" href="report.html">Open sample report</a>
            <a class="button secondary" href="leaderboard.html">Open sample leaderboard</a>
            <a class="button secondary" href="../index.html">Back to launch page</a>
          </div>
        </section>
        <section class="grid">
          <article class="card"><strong>{_e(sample['agentName'])}</strong><p>Overall {_e(sample['overall'])}; {_e(sample['tasksPassed'])}/{_e(sample['tasksTotal'])} tasks.</p></article>
          <article class="card"><strong>5 local-public pilots</strong><p>Deterministic fixture leaderboard for the first public beta package.</p></article>
          <article class="card"><strong>Boundary</strong><p>No hosted execution, no checkout, no credentials, no private task corpus.</p></article>
        </section>
        """,
    )


def _render_static_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    dimensions = summary["dimensions"]
    attempts = "".join(
        f"""
        <article class="card attempt">
          <strong>{_e(attempt['taskId'])}</strong>
          <p>{_e(attempt['verdict'])} · {_e(attempt['elapsedSeconds'])}s · {_e(attempt['category'])}</p>
          <p>{_e(attempt['answer'])}</p>
        </article>
        """
        for attempt in report["attempts"]
    )
    dimension_cards = "".join(
        f"<article class=\"card\"><strong>{_e(name)}</strong><p>{_e(value)}</p></article>"
        for name, value in dimensions.items()
    )
    return _page(
        "AgentStack Benchmark — sample report",
        f"""
        <section class="hero">
          <p class="eyebrow">Static local-public sample report</p>
          <h1>{_e(report['agent']['name'])}</h1>
          <p><strong>Overall {summary['overall']}</strong> · {summary['tasksPassed']}/{summary['tasksTotal']} tasks · Track {_e(report['track'])}</p>
          <div class="actions"><a class="button" href="leaderboard.html">View sample leaderboard</a><a class="button secondary" href="report.json">Open JSON</a></div>
        </section>
        <section class="grid">{dimension_cards}</section>
        <section><h2>Task attempts</h2><div class="grid">{attempts}</div></section>
        """,
    )


def _render_static_leaderboard(rows: list[dict[str, Any]], pilot_reports: list[dict[str, Any]]) -> str:
    boundaries = {item["agentId"]: item["report"].get("agent", {}).get("name", item["agentId"]) for item in pilot_reports}
    row_html = "".join(
        f"""
        <tr>
          <td>#{_e(row['rank'])}</td>
          <td>{_e(row['agentName'])}</td>
          <td>{_e(row['track'])}</td>
          <td>{_e(row['overall'])}</td>
          <td>{_e(row['tasksPassed'])}/{_e(row['tasksTotal'])}</td>
        </tr>
        """
        for row in rows
    )
    pilot_names = ", ".join(_e(value.split(" — ")[0]) for value in boundaries.values())
    return _page(
        "AgentStack Benchmark — sample leaderboard",
        f"""
        <section class="hero">
          <p class="eyebrow">Static local-public sample leaderboard</p>
          <h1>5-pilot deterministic fixture leaderboard.</h1>
          <p>{pilot_names}</p>
          <div class="actions"><a class="button" href="report.html">Open sample report</a><a class="button secondary" href="leaderboard.json">Open JSON</a></div>
        </section>
        <section class="card wide">
          <table><thead><tr><th>Rank</th><th>Agent stack</th><th>Track</th><th>Overall</th><th>Tasks</th></tr></thead><tbody>{row_html}</tbody></table>
        </section>
        """,
    )


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --card:#111d2d; --text:#edf5ff; --muted:#a8b7ca; --accent:#69e0ff; --ok:#7dffb2; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top left, #14395a, var(--bg) 48%); color:var(--text); }}
    main {{ width:min(1080px, calc(100% - 32px)); margin:0 auto; padding:56px 0; }}
    .hero,.card {{ background:rgba(17,29,45,.82); border:1px solid rgba(255,255,255,.12); border-radius:24px; padding:28px; box-shadow:0 20px 70px rgba(0,0,0,.25); }}
    .eyebrow {{ color:var(--ok); text-transform:uppercase; letter-spacing:.12em; font-weight:800; }}
    h1 {{ margin:0; font-size:clamp(36px, 7vw, 70px); line-height:.96; }}
    h2 {{ margin-top:32px; }}
    p {{ color:var(--muted); font-size:17px; line-height:1.55; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:22px; }}
    .button {{ display:inline-flex; padding:12px 18px; border-radius:999px; background:var(--accent); color:#06101d; text-decoration:none; font-weight:800; }}
    .button.secondary {{ background:rgba(255,255,255,.1); color:var(--text); border:1px solid rgba(255,255,255,.16); }}
    .grid {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:16px; margin-top:18px; }}
    .wide {{ margin-top:18px; overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:12px; border-bottom:1px solid rgba(255,255,255,.12); text-align:left; }}
    strong {{ color:var(--text); }}
    @media (max-width:800px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
