from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse

from .leaderboard import collect_leaderboard_rows

PRICING_MODE = "free-beta"
SERVICE_NAME = "agentstack-benchmark"


class BenchmarkAPIHandler(BaseHTTPRequestHandler):
    runs_dir: Path

    def do_GET(self) -> None:
        path = parse.urlparse(self.path).path
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
