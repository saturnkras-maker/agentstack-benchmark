from __future__ import annotations

import html
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse

from .leaderboard import collect_leaderboard_rows
from .run_registry import collect_run_summaries, load_run_report
from .runner import run_benchmark
from .security import InMemoryRateLimiter, SecurityConfig
from .tracks import build_track_capabilities

PRICING_MODE = "free-beta"
SERVICE_NAME = "agentstack-benchmark"
DEFAULT_TASK_PACK_PATH = Path(__file__).resolve().parents[2] / "examples/task_packs/mvp_v0.json"
_SAFE_FORM_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_DIMENSION_LABELS = {
    "autonomy": "Autonomy",
    "costEfficiency": "Cost efficiency",
    "depth": "Depth",
    "memorySkills": "Memory skills",
    "quality": "Quality",
    "reliability": "Reliability",
    "safety": "Safety",
    "speed": "Speed",
    "toolUse": "Tool use",
}


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
    button.button {{ border: 0; cursor: pointer; font: inherit; }}
    form {{ display: grid; gap: 14px; margin-top: 20px; }}
    label {{ display: grid; gap: 6px; font-weight: 700; }}
    input, select {{ width: 100%; box-sizing: border-box; border: 1px solid #34446d; border-radius: 12px; padding: 11px 12px; background: #10172d; color: #f6f8ff; font: inherit; }}
    input:focus-visible, select:focus-visible, .button:focus-visible {{ outline: 3px solid #8bd3ff; outline-offset: 2px; }}
    .callout {{ border: 1px solid #3d548b; background: #10172d; border-radius: 16px; padding: 14px; }}
    .error {{ border-color: #c06b6b; background: #2a1620; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #293657; vertical-align: top; }}
    .muted {{ color: #a9b5d6; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin: 16px 0; }}
    .metric {{ background: #10172d; border-radius: 14px; padding: 14px; }}
    .track-badge {{ display: inline-block; border: 1px solid #4f67a8; border-radius: 999px; padding: 2px 8px; color: #c9d6ff; background: #1b2748; font-size: 12px; font-weight: 700; }}
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


def _render_track_badge(track: str) -> str:
    return f'<span class="track-badge">{html.escape(track)}</span>'


def _display_dimension_name(name: str) -> str:
    return _DIMENSION_LABELS.get(name, name[:1].upper() + name[1:])


def _safe_form_value(values: dict[str, str], name: str, default: str = "") -> str:
    return html.escape(values.get(name, default), quote=True)


def _validate_form_segment(value: str, field_name: str) -> str:
    if not _SAFE_FORM_SEGMENT.fullmatch(value):
        raise ValueError(f"{field_name} must be 1-64 chars: letters, digits, dot, underscore, dash")
    if value in {".", ".."}:
        raise ValueError(f"{field_name} must be a safe path segment")
    return value


def _default_run_id(agent_id: str) -> str:
    return f"{agent_id}-{int(time.time())}"


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
            f"<br><span class=\"muted\">{html.escape(str(top['overall']))} overall · {_render_track_badge(str(top['track']))} · run <code>{html.escape(top_run_id)}</code></span></div>"
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
        <a class="button" href="/run">Run benchmark</a>
        <a href="/leaderboard">Open leaderboard</a>
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


def _render_run_form_page(values: dict[str, str] | None = None, error_message: str | None = None) -> str:
    values = values or {}
    error_block = ""
    if error_message:
        error_block = (
            "      <div class=\"callout error\"><strong>Run blocked</strong><br>"
            f"<span class=\"muted\">{html.escape(error_message)}</span></div>\n"
        )
    body = f"""    <section class="card">
      <p class="eyebrow">Hosted UX slice · local-public</p>
      <h1>Run benchmark</h1>
      <p class="muted">Connect a loopback HTTP adapter, run the MVP task pack, and open a visual score report from the browser.</p>
      <div class="callout">
        <strong>Safety boundary:</strong> this slice accepts only a loopback HTTP adapter on <code>127.0.0.1</code>, <code>localhost</code>, or <code>::1</code>. No API keys are accepted, stored, printed, or forwarded in this local-public preview.
      </div>
{error_block}      <form method="post" action="/run">
        <label>Agent ID
          <input name="agentId" required maxlength="64" pattern="[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}" value="{_safe_form_value(values, 'agentId', 'my-local-agent')}">
        </label>
        <label>Agent name
          <input name="name" required maxlength="120" value="{_safe_form_value(values, 'name', 'My Local Agent')}">
        </label>
        <label>Version
          <input name="version" required maxlength="40" value="{_safe_form_value(values, 'version', '0.1.0')}">
        </label>
        <label>HTTP endpoint
          <input name="endpoint" required value="{_safe_form_value(values, 'endpoint', 'http://127.0.0.1:8765/tasks')}">
        </label>
        <label>Run ID
          <input name="runId" maxlength="64" pattern="[A-Za-z0-9][A-Za-z0-9._-]{{0,63}}" value="{_safe_form_value(values, 'runId', '')}" placeholder="optional; generated from agentId if empty">
        </label>
        <button class="button" type="submit">Run benchmark</button>
      </form>
      <p class="muted">Task pack: <code>examples/task_packs/mvp_v0.json</code>. Track: <code>local-public</code>. External hosted endpoints/API-secret flow is intentionally reserved for the next authenticated runner slice.</p>
      <p><a href="/leaderboard">Back to leaderboard</a></p>
    </section>
"""
    return _render_page("Run AgentStack Benchmark", body)


def _render_run_complete_page(run_id: str, report: dict[str, Any]) -> str:
    summary = report["summary"]
    agent = report["agent"]
    quoted_run_id = _quote_run_id(run_id)
    dimensions = " · ".join(
        f"{html.escape(_display_dimension_name(str(name)))} {html.escape(str(value))}"
        for name, value in sorted(summary["dimensions"].items())
    )
    body = f"""    <section class="card">
      <p class="eyebrow">Run complete</p>
      <h1>Benchmark complete</h1>
      <p><strong>{html.escape(str(agent['name']))}</strong> <span class="muted">(<code>{html.escape(str(agent['agentId']))}</code>)</span></p>
      <div class="grid">
        <div class="metric"><strong>Overall</strong><br>{html.escape(str(summary['overall']))}</div>
        <div class="metric"><strong>Tasks</strong><br>{html.escape(str(summary['tasksPassed']))}/{html.escape(str(summary['tasksTotal']))}</div>
        <div class="metric"><strong>Track</strong><br>{_render_track_badge(str(report['track']))}</div>
      </div>
      <p class="muted">{dimensions}</p>
      <div class="actions">
        <a class="button" href="/runs/{quoted_run_id}">Open visual report</a>
        <a href="/leaderboard">View leaderboard</a>
        <a href="/api/v1/runs/{quoted_run_id}/report">JSON report</a>
        <a href="/run">Run another agent</a>
      </div>
    </section>
"""
    return _render_page("Benchmark complete", body)


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
                f"{html.escape(_display_dimension_name(str(name)))} {html.escape(str(value))}" for name, value in sorted(dimensions.items())
            )
            table_rows.append(
                "      <tr>"
                f"<td>#{row['rank']}</td>"
                f"<td><a href=\"/runs/{_quote_run_id(run_id)}\">{html.escape(str(row['agentName']))}</a>"
                f"<br><span class=\"muted\"><code>{html.escape(str(row['agentId']))}</code></span></td>"
                f"<td>{_render_track_badge(str(row['track']))}</td>"
                f"<td>{html.escape(str(row['overall']))}</td>"
                f"<td>{html.escape(str(row['tasksPassed']))}/{html.escape(str(row['tasksTotal']))}</td>"
                f"<td class=\"muted\">{dimension_text}</td>"
                "</tr>"
            )
        table = """      <table>
        <thead><tr><th>Rank</th><th>Agent</th><th>Track</th><th>Overall</th><th>Tasks</th><th>Dimensions</th></tr></thead>
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
    track = str(report["track"])
    dimensions = summary["dimensions"]
    metric_cards = "\n".join(
        f"      <div class=\"metric\"><strong>{html.escape(_display_dimension_name(str(name)))}</strong><br>{html.escape(str(value))}</div>"
        for name, value in sorted(dimensions.items())
    )
    safe_run_id = html.escape(run_id)
    quoted_run_id = _quote_run_id(run_id)
    body = f"""    <section class="card">
      <p class="eyebrow">Run report</p>
      <h1>Run report: {safe_run_id}</h1>
      <p>{_render_track_badge(track)}</p>
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
    security_config: SecurityConfig
    rate_limiter: InMemoryRateLimiter

    def do_GET(self) -> None:
        path = parse.urlparse(self.path).path
        if path != "/api/v1/healthz":
            if not self._authorize_request():
                return
            if not self._check_rate_limit():
                return
        if path == "/":
            self._send_html(_render_home_page(self.runs_dir))
            return
        if path == "/run":
            self._send_html(_render_run_form_page())
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
                    "security": self.security_config.to_public_dict(),
                }
            )
            return
        if path == "/api/v1/tracks":
            self._send_json(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "trackCapabilities": build_track_capabilities(),
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
                    "track": report["track"],
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

    def do_POST(self) -> None:
        path = parse.urlparse(self.path).path
        if not self._authorize_request():
            return
        if not self._check_rate_limit():
            return
        if path != "/run":
            self._send_html(_render_error_page("Not found", f"Unsupported endpoint: {path}"), status=404)
            return
        form = self._read_urlencoded_form()
        if form is None:
            return
        try:
            run_id, report = self._run_browser_benchmark(form)
        except ValueError as exc:
            self._send_html(_render_run_form_page(form, str(exc)), status=400)
            return
        self._send_html(_render_run_complete_page(run_id, report))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_urlencoded_form(self) -> dict[str, str] | None:
        content_type = self.headers.get_content_type()
        if content_type != "application/x-www-form-urlencoded":
            self._send_html(
                _render_run_form_page(error_message="Content-Type must be application/x-www-form-urlencoded"),
                status=415,
            )
            return None
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_html(_render_run_form_page(error_message="Invalid Content-Length"), status=400)
            return None
        if content_length > 8192:
            self._send_html(_render_run_form_page(error_message="Form body is too large"), status=413)
            return None
        raw_body = self.rfile.read(content_length).decode("utf-8")
        parsed = parse.parse_qs(raw_body, keep_blank_values=True)
        return {name: values[0].strip() for name, values in parsed.items() if values}

    def _run_browser_benchmark(self, form: dict[str, str]) -> tuple[str, dict[str, Any]]:
        agent_id = _validate_form_segment(form.get("agentId", ""), "agentId")
        name = form.get("name", "").strip()
        if not name:
            raise ValueError("name is required")
        version = form.get("version", "").strip() or "0.1.0"
        endpoint = form.get("endpoint", "").strip()
        if not endpoint:
            raise ValueError("endpoint is required")
        run_id = form.get("runId", "").strip() or _default_run_id(agent_id)
        run_id = _validate_form_segment(run_id, "runId")
        if load_run_report(self.runs_dir, run_id) is not None:
            raise ValueError(f"runId already exists: {run_id}")

        manifest = {
            "agentId": agent_id,
            "name": name[:120],
            "version": version[:40],
            "adapter": {
                "type": "http",
                "endpoint": endpoint,
            },
            "limits": {
                "timeoutSecondsPerTask": 10,
                "maxRunsPerTask": 1,
            },
        }
        manifest_path = self.runs_dir / "_submitted_manifests" / f"{run_id}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        report = run_benchmark(manifest_path, DEFAULT_TASK_PACK_PATH, self.runs_dir / run_id)
        return run_id, report

    def _authorize_request(self) -> bool:
        allowed, status, code, message = self.security_config.validate_authorization_header(
            self.headers.get("Authorization")
        )
        if allowed:
            return True
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        self._send_json({"error": {"code": code, "message": message}}, status=status, headers=headers)
        return False

    def _check_rate_limit(self) -> bool:
        client_id = self.client_address[0] if self.client_address else "unknown"
        allowed, retry_after = self.rate_limiter.check(client_id)
        if allowed:
            return True
        self._send_json(
            {
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Rate limit exceeded",
                }
            },
            status=429,
            headers={"Retry-After": str(retry_after)},
        )
        return False

    def _send_json(
        self,
        body: dict[str, Any],
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
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


def make_server(
    host: str,
    port: int,
    runs_dir: str | Path,
    security_config: SecurityConfig | None = None,
) -> ThreadingHTTPServer:
    runs_path = Path(runs_dir)
    resolved_security_config = security_config or SecurityConfig.disabled()

    class ConfiguredBenchmarkAPIHandler(BenchmarkAPIHandler):
        pass

    ConfiguredBenchmarkAPIHandler.runs_dir = runs_path
    ConfiguredBenchmarkAPIHandler.security_config = resolved_security_config
    ConfiguredBenchmarkAPIHandler.rate_limiter = InMemoryRateLimiter(resolved_security_config)
    return ThreadingHTTPServer((host, port), ConfiguredBenchmarkAPIHandler)


def serve(
    host: str,
    port: int,
    runs_dir: str | Path,
    security_config: SecurityConfig | None = None,
) -> None:
    resolved_security_config = security_config or SecurityConfig.disabled()
    server = make_server(host, port, runs_dir, security_config=resolved_security_config)
    try:
        print(
            json.dumps(
                {
                    "service": SERVICE_NAME,
                    "pricingMode": PRICING_MODE,
                    "url": f"http://{host}:{server.server_port}",
                    "runsDir": str(Path(runs_dir)),
                    "security": resolved_security_config.to_public_dict(),
                },
                ensure_ascii=False,
            )
        )
        server.serve_forever()
    finally:
        server.server_close()
