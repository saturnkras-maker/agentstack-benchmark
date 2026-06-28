from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

RESPONSE_SCHEMA_VERSION = "agentstack-benchmark.adapter.response.v0.1"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

# Configured in main(); a real local Claude Code (Haiku) adapter over the
# AgentStack HTTP adapter contract v0.1. Loopback-only, subscription-only.
CONFIG = {
    "claude_bin": "/Users/vladimirknaz/.local/bin/claude",
    "model": "claude-haiku-4-5-20251001",
    "call_timeout": 100.0,
}


def _clean_env() -> dict[str, str]:
    """Child env with every ANTHROPIC_* variable stripped.

    Guarantees no ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL
    can route the call to paid API billing; the call must use the logged-in
    Max subscription. Everything else (HOME, PATH, ...) is preserved so the
    Claude CLI can find its config and auth.
    """
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("ANTHROPIC_")}


def _build_prompt(task: dict) -> str:
    prompt = str(task.get("prompt", ""))
    context = task.get("context", {})
    if context:
        prompt = prompt + "\n\nContext (JSON):\n" + json.dumps(context, ensure_ascii=False)
    return prompt


def _call_claude(prompt: str) -> tuple[bool, str, str]:
    cmd = [CONFIG["claude_bin"], "-p", prompt, "--model", CONFIG["model"]]
    try:
        result = subprocess.run(
            cmd,
            env=_clean_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=float(CONFIG["call_timeout"]),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "", f"claude_timeout_after_{CONFIG['call_timeout']}s"
    except Exception as exc:  # noqa: BLE001 - surface any spawn failure as runtime error
        return False, "", f"claude_spawn_error={exc}"
    if result.returncode != 0:
        return False, "", f"returncode={result.returncode}; stderr={result.stderr[-1200:].strip()}"
    return True, result.stdout.strip(), ""


class ClaudeAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/tasks":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            task = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"answer": "", "toolTrace": [], "runtimeError": "invalid_request_json"})
            return

        task_id = task.get("taskId", "?")
        prompt = _build_prompt(task)
        started = time.monotonic()
        ok, answer, err = _call_claude(prompt)
        elapsed = time.monotonic() - started

        if not ok:
            sys.stderr.write(f"[claude-agent] task={task_id} FAILED in {elapsed:.1f}s: {err}\n")
            sys.stderr.flush()
            self._send_json(
                200,
                {"schemaVersion": RESPONSE_SCHEMA_VERSION, "answer": "", "toolTrace": [], "runtimeError": err},
            )
            return

        preview = answer.replace("\n", " ")[:120]
        sys.stderr.write(
            f"[claude-agent] task={task_id} ok in {elapsed:.1f}s chars={len(answer)} :: {preview}\n"
        )
        sys.stderr.flush()
        self._send_json(
            200,
            {"schemaVersion": RESPONSE_SCHEMA_VERSION, "answer": answer, "toolTrace": []},
        )

    def _send_json(self, status: int, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real local Claude Code HTTP adapter (subscription, loopback-only)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--claude-bin", default="/Users/vladimirknaz/.local/bin/claude")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--call-timeout", type=float, default=100.0)
    args = parser.parse_args()

    if args.host not in LOOPBACK_HOSTS:
        sys.stderr.write(f"[claude-agent] refusing non-loopback host: {args.host}\n")
        return 2

    CONFIG["claude_bin"] = args.claude_bin
    CONFIG["model"] = args.model
    CONFIG["call_timeout"] = args.call_timeout

    leaked = sorted(k for k in os.environ if k.upper().startswith("ANTHROPIC_"))
    sys.stderr.write(
        f"[claude-agent] listening on http://{args.host}:{args.port}/tasks model={args.model} "
        f"call_timeout={args.call_timeout}s anthropic_env_stripped={leaked or 'none'}\n"
    )
    sys.stderr.flush()

    server = HTTPServer((args.host, args.port), ClaudeAgentHandler)
    print(json.dumps({"url": f"http://{args.host}:{args.port}/tasks", "model": args.model}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
