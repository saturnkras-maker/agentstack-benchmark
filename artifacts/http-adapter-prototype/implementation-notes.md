# HTTP adapter prototype implementation notes

## Scope

- Add a local-only HTTP adapter prototype to the AgentStack Benchmark runner.
- Keep the adapter contract small: POST the same JSON task payload used by the CLI adapter and expect a JSON object agent response.
- Do not call external APIs; tests use a stdlib `HTTPServer` bound to `127.0.0.1` on an ephemeral port.

## Starting state

- `git status --short` was clean before changes.
- Starting head: `8d837b3 feat: add static leaderboard builder`.

## Decisions / assumptions

- Manifest field chosen for HTTP endpoint: `adapter.endpoint`.
- The HTTP prototype is intentionally local-only. The runner rejects non-local hostnames to prevent accidental external network side effects in this slice.
- The HTTP payload matches the CLI payload: `taskId`, `category`, `prompt`, `context`.

## Verification log

- RED: `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_http_adapter_posts_tasks_to_local_endpoint -v` failed as expected because `runner.py` still routed every manifest through `_invoke_cli_agent` and rejected `adapter.type == "http"` with `ValueError: Only cli adapter is supported in prototype v0.1`.
- GREEN specific: `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_http_adapter_posts_tasks_to_local_endpoint -v` passed after adding HTTP dispatch, local endpoint validation, and stdlib `urllib` POST support.
- GREEN suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed: 4 tests in 1.016s.
- Docs/example: added `examples/manifests/mock_http.json`; README now documents local-only HTTP adapter contract and usage.
- Final compile gate: `python3 -m compileall -q src examples tests` exited 0 with no stdout.
- Final unittest gate: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed: 4 tests in 1.014s.
