from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from mock_good_agent import ANSWERS

RESPONSE_SCHEMA_VERSION = "agentstack-benchmark.adapter.response.v0.1"


class ContractAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/tasks":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        task = json.loads(self.rfile.read(content_length).decode("utf-8"))
        answer = dict(ANSWERS.get(task["taskId"], {"answer": "unknown task", "toolTrace": []}))
        answer.setdefault("toolTrace", [])
        answer["schemaVersion"] = RESPONSE_SCHEMA_VERSION
        payload = json.dumps(answer, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Example AgentStack Benchmark HTTP adapter")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), ContractAgentHandler)
    print(json.dumps({"url": f"http://{args.host}:{server.server_port}/tasks"}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
