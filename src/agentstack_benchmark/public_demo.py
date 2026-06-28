from __future__ import annotations

import copy
import html
import json
import shutil
from pathlib import Path
from typing import Any

from .leaderboard import build_leaderboard
from .evaluator import SCORING_WEIGHTS, summarize_scores
from .offline_demo import run_offline_demo_once
from .pilots import DEFAULT_PILOT_REGISTRY_PATH, load_pilot_registry, run_local_pilots
from .reproducibility import build_reproducibility_metadata
from .schemas import stable_json_hash

PUBLIC_DEMO_SCHEMA_VERSION = "agentstack-benchmark.public-demo.v0.1"

# Committed real, honest-scored frontier run used to drive the PUBLIC leaderboard.
# When present, the public leaderboard reflects the honest engine's true frontier
# ranking (Opus > Sonnet > Haiku, with a handicapped-weak control) instead of the
# old deterministic 5-pilot fixture that flattened every stack to a near-tie. Real
# speed and overall are preserved verbatim — they are NOT clobbered to 100 — so the
# public surface shows honest differentiation. Falls back to the pilot fixtures
# only if this committed run is missing.
PUBLIC_FRONTIER_RUN_DIR = "artifacts/frontier-validation/run2"


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
    sample_report = _make_static_sample_report(
        json.loads(sample_report_path.read_text(encoding="utf-8"))
    )

    pilot_runs_dir = generated_dir / "runs" / "pilots"
    registry_path = repo_root / DEFAULT_PILOT_REGISTRY_PATH
    registry = load_pilot_registry(registry_path)
    pilot_reports = run_local_pilots(
        registry_path=registry_path,
        task_pack_path=repo_root / "examples/task_packs/mvp_v0.json",
        out_dir=pilot_runs_dir,
    )
    leaderboard_path = generated_dir / "pilot-leaderboard.json"

    # Prefer the committed real, honest-scored frontier run for the public
    # leaderboard so it shows the true Opus > Sonnet > Haiku ranking under the
    # honest engine. Fall back to the deterministic pilot fixtures only if the
    # frontier run is absent.
    frontier_run_dir = repo_root / PUBLIC_FRONTIER_RUN_DIR
    if _has_run_reports(frontier_run_dir):
        raw_rows = build_leaderboard(frontier_run_dir, leaderboard_path)
        leaderboard_rows = _make_honest_leaderboard_rows(raw_rows)
        leaderboard_source = "real-frontier-run-honest-scoring"
        leaderboard_title = "Honest frontier leaderboard — Opus &gt; Sonnet &gt; Haiku."
        leaderboard_caption = (
            "Real local-public runs scored by the honest engine "
            "(scoring_schema_v1 + opt-in LLM-judge). Speed and overall are the "
            "true measured values, not flattened placeholders."
        )
    else:
        raw_rows = build_leaderboard(pilot_runs_dir, leaderboard_path)
        leaderboard_rows = _make_static_leaderboard_rows(raw_rows)
        leaderboard_source = "deterministic-pilot-fixtures"
        leaderboard_title = "5-pilot deterministic fixture leaderboard."
        leaderboard_caption = ""

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
            "source": leaderboard_source,
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
        _render_static_leaderboard(
            leaderboard_rows,
            pilot_reports,
            title=leaderboard_title,
            caption=leaderboard_caption,
        ),
        encoding="utf-8",
    )
    shutil.rmtree(generated_dir)
    return public_demo_manifest


def _make_static_sample_report(report: dict[str, Any]) -> dict[str, Any]:
    """Normalize timing-derived values so committed static demo files are reproducible."""

    static_report = copy.deepcopy(report)
    static_report["agent"]["manifestHash"] = stable_json_hash(
        {
            "staticSample": True,
            "track": static_report["track"],
            "agentId": static_report["agent"]["agentId"],
            "taskPackId": static_report["taskPack"]["taskPackId"],
        }
    )
    for attempt in static_report["attempts"]:
        attempt["elapsedSeconds"] = 0.0
        attempt["scores"]["speed"] = 100.0
    static_report["summary"] = summarize_scores(static_report["attempts"])
    static_report["reproducibility"] = build_reproducibility_metadata(
        static_report,
        redacted_occurrences=0,
    )
    return static_report


def _make_static_leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    static_rows = []
    for row in sorted(rows, key=lambda item: item["agentId"]):
        sanitized = _sanitize_leaderboard_row(row)
        sanitized["dimensions"] = dict(sanitized["dimensions"])
        sanitized["dimensions"]["speed"] = 100.0
        sanitized["overall"] = _weighted_overall_from_dimensions(sanitized["dimensions"])
        static_rows.append(sanitized)
    static_rows.sort(key=lambda item: (-float(item["overall"]), item["agentId"]))
    for index, row in enumerate(static_rows, start=1):
        row["rank"] = index
    return static_rows


def _has_run_reports(runs_dir: Path) -> bool:
    """True if ``runs_dir`` holds at least one ``<run>/report.json`` to rank."""
    runs_dir = Path(runs_dir)
    if not runs_dir.is_dir():
        return False
    return any(child.joinpath("report.json").is_file() for child in runs_dir.iterdir() if child.is_dir())


def _make_honest_leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Static rows for the public leaderboard that PRESERVE honest scoring.

    Unlike :func:`_make_static_leaderboard_rows` (the legacy fixture path, which
    overwrites ``speed`` with 100 and recomputes ``overall`` — flattening real
    differences), this keeps the real measured ``overall``/``speed`` and ranking
    from the honest engine. Only the report path is sanitized; ordering is the
    leaderboard's own honest rank.
    """
    static_rows: list[dict[str, Any]] = []
    for row in rows:
        sanitized = _sanitize_leaderboard_row(row)
        sanitized["dimensions"] = dict(sanitized["dimensions"])
        static_rows.append(sanitized)
    static_rows.sort(key=lambda item: (-float(item["overall"]), item["agentId"]))
    for index, row in enumerate(static_rows, start=1):
        row["rank"] = index
    return static_rows


def _weighted_overall_from_dimensions(dimensions: dict[str, Any]) -> float:
    return round(
        sum(float(dimensions[key]) * weight for key, weight in SCORING_WEIGHTS.items()),
        2,
    )


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


def _render_static_leaderboard(
    rows: list[dict[str, Any]],
    pilot_reports: list[dict[str, Any]],
    title: str = "5-pilot deterministic fixture leaderboard.",
    caption: str = "",
) -> str:
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
    if caption:
        subline = _e(caption)
    else:
        subline = ", ".join(_e(value.split(" — ")[0]) for value in boundaries.values())
    return _page(
        "AgentStack Benchmark — sample leaderboard",
        f"""
        <section class="hero">
          <p class="eyebrow">Static local-public sample leaderboard</p>
          <h1>{title}</h1>
          <p>{subline}</p>
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
