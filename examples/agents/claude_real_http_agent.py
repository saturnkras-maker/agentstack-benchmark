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
    # Resilience to transient subscription throttling (rate-limit error OR a
    # success-exit-with-empty-stdout). Without retries one throttle cascades into
    # a wall of empty/failed tasks; see _call_claude.
    "max_attempts": 4,
    "retry_backoff": 4.0,
    # Optional handicap: an extra system prompt appended to the real CLI call.
    # Used to build a DELIBERATELY-WEAK real agent on a competent model (e.g.
    # "answer in <=5 words, no reasoning") so the leaderboard spans weak->strong
    # on REAL inference. Empty string = no handicap (normal tier).
    "system_prompt": "",
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
    # Optional handicap: prepend a hard output constraint into the USER turn.
    # (Claude Code's --append-system-prompt is overridden by its default system
    # prompt and was ignored in practice, so the handicap rides in the user
    # turn where it is actually obeyed.) Real inference, real model, intentionally
    # shallow output; no answer content is ever fabricated.
    system_prompt = str(CONFIG.get("system_prompt") or "")
    if system_prompt:
        prompt = system_prompt + "\n\n" + prompt
    return prompt


_RATE_LIMIT_MARKERS = (
    "rate limit", "rate_limit", "429", "overloaded", "too many requests",
    "quota", "usage limit", "please try again", "temporarily",
)


def _looks_throttled(stderr: str) -> bool:
    low = stderr.lower()
    return any(marker in low for marker in _RATE_LIMIT_MARKERS)


def _call_claude_once(prompt: str) -> tuple[bool, str, str]:
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


def _call_claude(prompt: str) -> tuple[bool, str, str]:
    """Call the CLI, retrying transient throttles with exponential backoff.

    Under sustained sequential load (and especially with the LLM-judge doubling
    the subscription call rate), the CLI can transiently return either a
    rate-limit error OR a SUCCESS exit with EMPTY stdout. Treating that as a real
    empty answer makes one throttle cascade into a wall of empty/failed tasks. We
    therefore retry on (a) a throttle-looking failure and (b) an empty-but-ok
    response, with growing sleeps, before giving up. A genuinely empty model reply
    is rare and, after the retries, still surfaces as an empty answer (no fake
    content is ever fabricated).
    """
    attempts = int(CONFIG.get("max_attempts", 4))
    backoff = float(CONFIG.get("retry_backoff", 4.0))
    last: tuple[bool, str, str] = (False, "", "no_attempt")
    for i in range(attempts):
        ok, answer, err = _call_claude_once(prompt)
        if ok and answer:
            return True, answer, ""
        last = (ok, answer, err)
        transient = (ok and not answer) or _looks_throttled(err)
        if not transient or i == attempts - 1:
            break
        sleep_s = backoff * (2 ** i)
        sys.stderr.write(
            f"[claude-agent] transient (ok={ok} empty={not answer} err={err[:80]!r}); "
            f"retry {i + 1}/{attempts - 1} after {sleep_s:.1f}s\n"
        )
        sys.stderr.flush()
        time.sleep(sleep_s)
    if last[0] and not last[1]:
        return False, "", "claude_empty_output_after_retries (likely subscription throttle)"
    return last


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
    parser.add_argument(
        "--max-attempts", type=int, default=4,
        help="Total CLI attempts per task; transient throttles/empty replies are retried.",
    )
    parser.add_argument(
        "--retry-backoff", type=float, default=4.0,
        help="Base seconds for exponential backoff between throttle retries.",
    )
    parser.add_argument(
        "--system-prompt", default="",
        help=(
            "Optional handicap system prompt appended to every real CLI call "
            "(e.g. 'Answer in <=5 words, no reasoning'). Builds a deliberately-"
            "weak real agent for weak->strong leaderboard spread. Empty = normal."
        ),
    )
    args = parser.parse_args()

    if args.host not in LOOPBACK_HOSTS:
        sys.stderr.write(f"[claude-agent] refusing non-loopback host: {args.host}\n")
        return 2

    CONFIG["max_attempts"] = args.max_attempts
    CONFIG["retry_backoff"] = args.retry_backoff
    CONFIG["claude_bin"] = args.claude_bin
    CONFIG["model"] = args.model
    CONFIG["call_timeout"] = args.call_timeout
    CONFIG["system_prompt"] = args.system_prompt

    leaked = sorted(k for k in os.environ if k.upper().startswith("ANTHROPIC_"))
    sys.stderr.write(
        f"[claude-agent] listening on http://{args.host}:{args.port}/tasks model={args.model} "
        f"call_timeout={args.call_timeout}s anthropic_env_stripped={leaked or 'none'} "
        f"handicap={'yes:' + args.system_prompt if args.system_prompt else 'none'}\n"
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
