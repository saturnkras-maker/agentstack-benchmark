from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse

from .leaderboard import collect_leaderboard_rows
from .run_registry import collect_run_summaries, load_run_report

PRICING_MODE = "free-beta"
SERVICE_NAME = "agentstack-benchmark"


def _quote_run_id(run_id: str) -> str:
    return parse.quote(run_id, safe="")


def _rank_run_summaries(runs_dir: str | Path) -> list[dict[str, Any]]:
    rows = sorted(
        collect_run_summaries(runs_dir),
        key=lambda item: (-float(item["overall"]), str(item["agentId"]), str(item["runId"])),
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _render_page(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #0b1020; color: #f6f8ff; line-height: 1.5; }}
    a {{ color: #8bd3ff; }}
    .shell {{ max-width: 960px; margin: 0 auto; padding: 40px 20px 56px; }}
    .hero, .card {{ background: #141b34; border: 1px solid #273457; border-radius: 20px; padding: 24px; box-shadow: 0 18px 60px rgba(0, 0, 0, 0.22); }}
    .hero {{ margin-bottom: 16px; }}
    .eyebrow {{ color: #9fb0d8; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; font-weight: 700; }}
    h1 {{ margin: 8px 0 12px; font-size: clamp(32px, 5vw, 56px); }}
    h2 {{ margin: 24px 0 12px; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }}
    .button {{ display: inline-block; border-radius: 999px; padding: 10px 16px; background: #2f7cff; color: white; text-decoration: none; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #293657; vertical-align: top; }}
    .muted {{ color: #a9b5d6; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin: 16px 0; }}
    .metric {{ background: #10172d; border-radius: 14px; padding: 14px; }}
    code {{ background: #10172d; border-radius: 6px; padding: 2px 5px; }}
  </style>
</head>
<body>
  <main class="shell">
{body}
  </main>
</body>
</html>
"""


def _render_home_page(runs_dir: str | Path) -> str:
    rows = _rank_run_summaries(runs_dir)
    top = rows[0] if rows else None
    if top is None:
        top_card = """      <div class="metric"><strong>No runs yet</strong><br><span class="muted">Generate a local report first.</span></div>"""
    else:
        top_run_id = str(top["runId"])
        top_card = (
            "      <div class=\"metric\"><strong>Current leader</strong><br>"
            f"<a href=\"/runs/{_quote_run_id(top_run_id)}\">{html.escape(str(top['agentName']))}</a>"
            f"<br><span class=\"muted\">{html.escape(str(top['overall']))} overall · run <code>{html.escape(top_run_id)}</code></span></div>"
        )
    run_links = "\n".join(
        f"        <li><a href=\"/runs/{_quote_run_id(str(row['runId']))}\">{html.escape(str(row['runId']))}</a> — {html.escape(str(row['agentName']))}</li>"
        for row in rows[:5]
    )
    if not run_links:
        run_links = "        <li class=\"muted\">No local run reports found.</li>"
    body = f"""    <section class="hero">
      <p class="eyebrow">Free beta · public beta preview</p>
      <h1>AgentStack Benchmark</h1>
      <p class="muted">Local read-only web surface for comparing agent stack runs from existing report artifacts.</p>
      <div class="grid">
        <div class="metric"><strong>{len(rows)} local runs</strong><br><span class="muted">Read from existing <code>report.json</code> files only.</span></div>
{top_card}
      </div>
      <div class="actions">
        <a class="button" href="/leaderboard">Open leaderboard</a>
        <a href="/api/v1/healthz">Health JSON</a>
        <a href="/api/v1/runs">Runs JSON</a>
      </div>
    </section>
    <section class="card">
      <h2>Recent local runs</h2>
      <ul>
{run_links}
      </ul>
      <p class="muted">No external deploy, live sends, billing, private-key handling, or remote execution happens in this preview.</p>
    </section>
"""
    return _render_page("AgentStack Benchmark", body)


def _render_leaderboard_page(runs_dir: str | Path) -> str:
    rows = _rank_run_summaries(runs_dir)
    if not rows:
        table = "      <p class=\"muted\">No local run reports found.</p>"
    else:
        table_rows = []
        for row in rows:
            run_id = str(row["runId"])
            dimensions = row["dimensions"]
            dimension_text = " · ".join(
                f"{html.escape(str(name))} {html.escape(str(value))}" for name, value in sorted(dimensions.items())
            )
            table_rows.append(
                "      <tr>"
                f"<td>#{row['rank']}</td>"
                f"<td><a href=\"/runs/{_quote_run_id(run_id)}\">{html.escape(str(row['agentName']))}</a>"
                f"<br><span class=\"muted\"><code>{html.escape(str(row['agentId']))}</code></span></td>"
                f"<td>{html.escape(str(row['overall']))}</td>"
                f"<td>{html.escape(str(row['tasksPassed']))}/{html.escape(str(row['tasksTotal']))}</td>"
                f"<td class=\"muted\">{dimension_text}</td>"
                "</tr>"
            )
        table = """      <table>
        <thead><tr><th>Rank</th><th>Agent</th><th>Overall</th><th>Tasks</th><th>Dimensions</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>""".format(rows="\n".join(table_rows))
    body = f"""    <section class="card">
      <p class="eyebrow">Free beta</p>
      <h1>Leaderboard</h1>
      <p class="muted">Ranked from local read-only <code>report.json</code> artifacts.</p>
{table}
      <p><a href="/">Back home</a> · <a href="/api/v1/leaderboard">JSON API</a></p>
    </section>
"""
    return _render_page("AgentStack Benchmark Leaderboard", body)


def _render_run_report_page(run_id: str, report: dict[str, Any]) -> str:
    agent = report["agent"]
    task_pack = report["taskPack"]
    summary = report["summary"]
    dimensions = summary["dimensions"]
    metric_cards = "\n".join(
        f"      <div class=\"metric\"><strong>{html.escape(str(name))}</strong><br>{html.escape(str(value))}</div>"
        for name, value in sorted(dimensions.items())
    )
    safe_run_id = html.escape(run_id)
    quoted_run_id = _quote_run_id(run_id)
    body = f"""    <section class="card">
      <p class="eyebrow">Run report</p>
      <h1>Run report: {safe_run_id}</h1>
      <p><strong>{html.escape(str(agent['name']))}</strong> <span class="muted">(<code>{html.escape(str(agent['agentId']))}</code>, version {html.escape(str(agent['version']))})</span></p>
      <p class="muted">Task pack: {html.escape(str(task_pack['name']))} · {html.escape(str(task_pack['version']))}</p>
      <div class="grid">
        <div class="metric"><strong>Overall</strong><br>{html.escape(str(summary['overall']))}</div>
        <div class="metric"><strong>tasks passed</strong><br>{html.escape(str(summary['tasksPassed']))}/{html.escape(str(summary['tasksTotal']))} tasks</div>
      </div>
      <h2>Dimensions</h2>
      <div class="grid">
{metric_cards}
      </div>
      <p><a href="/leaderboard">Back to leaderboard</a> · <a href="/api/v1/runs/{quoted_run_id}/report">JSON API report</a></p>
    </section>
"""
    return _render_page(f"Run report: {run_id}", body)


def _render_error_page(title: str, message: str) -> str:
    body = f"""    <section class="card">
      <p class="eyebrow">Error</p>
      <h1>{html.escape(title)}</h1>
      <p class="muted">{html.escape(message)}</p>
      <p><a href="/leaderboard">Back to leaderboard</a></p>
    </section>
"""
    return _render_page(title, body)


class BenchmarkAPIHandler(BaseHTTPRequestHandler):
    runs_dir: Path

    def do_GET(self) -> None:
        path = parse.urlparse(self.path).path
        if path == "/":
            self._send_html(_render_home_page(self.runs_dir))
            return
        if path == "/leaderboard":
            self._send_html(_render_leaderboard_page(self.runs_dir))
            return
        parts = path.split("/")
        if len(parts) == 3 and parts[1] == "runs" and parts[2]:
            run_id = parse.unquote(parts[2])
            try:
                report = load_run_report(self.runs_dir, run_id)
            except ValueError:
                self._send_html(
                    _render_error_page("Invalid run id", "INVALID_RUN_ID: runId must be a safe path segment"),
                    status=400,
                )
                return
            if report is None:
                self._send_html(
                    _render_error_page("Run not found", "No local report exists for this runId"),
                    status=404,
                )
                return
            self._send_html(_render_run_report_page(run_id, report))
            return
        if path == "/api/v1/healthz":
            self._send_json(
                {
                    "status": "ok",
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                }
            )
            return
        if path == "/api/v1/leaderboard":
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "entries": collect_leaderboard_rows(self.runs_dir),
                }
            )
            return
        if path == "/api/v1/runs":
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "runs": collect_run_summaries(self.runs_dir),
                }
            )
            return
        parts = path.split("/")
        if len(parts) == 6 and parts[1:4] == ["api", "v1", "runs"] and parts[5] == "report":
            run_id = parse.unquote(parts[4])
            try:
                report = load_run_report(self.runs_dir, run_id)
            except ValueError:
                self._send_json(
                    {
                        "error": {
                            "code": "INVALID_RUN_ID",
                            "message": "runId must be a safe path segment",
                        }
                    },
                    status=400,
                )
                return
            if report is None:
                self._send_json(
                    {
                        "error": {
                            "code": "RUN_NOT_FOUND",
                            "message": f"Run not found: {run_id}",
                        }
                    },
                    status=404,
                )
                return
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "runId": run_id,
                    "report": report,
                }
            )
            return
        self._send_json(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Unsupported endpoint: {path}",
                }
            },
            status=404,
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, body: dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, body: str, status: int = 200) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def make_server(host: str, port: int, runs_dir: str | Path) -> ThreadingHTTPServer:
    runs_path = Path(runs_dir)

    class ConfiguredBenchmarkAPIHandler(BenchmarkAPIHandler):
        pass

    ConfiguredBenchmarkAPIHandler.runs_dir = runs_path
    return ThreadingHTTPServer((host, port), ConfiguredBenchmarkAPIHandler)


def serve(host: str, port: int, runs_dir: str | Path) -> None:
    server = make_server(host, port, runs_dir)
    try:
        print(
            json.dumps(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "url": f"http://{host}:{server.server_port}",
                    "runsDir": str(Path(runs_dir)),
                },
                ensure_ascii=False,
            )
        )
        server.serve_forever()
    finally:
        server.server_close()
