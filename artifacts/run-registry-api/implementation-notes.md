# Run registry/report API implementation notes

## Scope

- Add the next local launch foundation for AgentStack Benchmark public beta: read-only API over existing `artifacts/runs/*/report.json` artifacts.
- No run execution endpoint, no POST execution surface, no deploy/live send/payment/billing/private-key flow.
- Keep the implementation stdlib-only.

## Decisions / assumptions

- API shape for this slice:
  - `GET /api/v1/runs` returns deterministic run summaries from immediate child directories under `runs_dir` that contain `report.json`.
  - `GET /api/v1/runs/{runId}/report` returns one existing report using only a safe single path segment as `runId`.
- Invalid/unsafe `runId` values should fail before filesystem lookup.
- Missing runs should return a JSON 404 without leaking local secret/config paths.

## Context basis / read set

- Manifest refreshed at `/tmp/hermes-agentstack-benchmark-manifest.json` before edits; repo count 38 files.
- Read unchanged routing/project files by hash:
  - `README.md` sha256 `762055f2593d04da1eb5b5d6aac8ba6ff0aa79500f05839b97157eb7d7bdce7c`
  - `src/agentstack_benchmark/server.py` sha256 `cfced8aa1a0a30ecbd38b1605529b56afff4d1622494f2ec2c64290fc23b0c03`
  - `src/agentstack_benchmark/leaderboard.py` sha256 `633cff42aa7ce5baddb2a83b0e0253c9e2d22cc72a7adb14a82178fd6b72bcd9`
  - `src/agentstack_benchmark/runner.py` sha256 `250be562a0691a1db2344d2ec9e010e9a3b66dca2b93855e3a24811bd80a6a12`
  - `src/agentstack_benchmark/cli.py` sha256 `ff21ae9204f43cfc85db0aca04fa4828ea7e4b995f8feefd364d60594fcdc313`
  - `tests/test_server.py` sha256 `a6dd7fbbddf30d383957b7e0b181ebda9cfc593890960257a7d7e4ffebf1ad87`
  - `tests/test_runner.py` sha256 `0e7f939dda5be14f480a6323dde78768879443594bf17436d02dca9e36210cbf`

## Verification log

- Preflight: `git status --short` clean; `git log --oneline -3` showed `4770e94`, `656a116`, `7ceb534`.
- RED 1: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests.test_runs_endpoint_lists_existing_report_summaries -v` failed as expected with `HTTP Error 404: Not Found` for missing `GET /api/v1/runs`.
- GREEN 1: same targeted test passed after adding `run_registry.collect_run_summaries()` and `GET /api/v1/runs`.
- RED 2: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests.test_run_report_endpoint_returns_one_existing_report -v` failed as expected with `HTTP Error 404: Not Found` for missing `GET /api/v1/runs/{runId}/report`.
- GREEN 2: same targeted test passed after adding `run_registry.load_run_report()` and the report endpoint.
- RED 3: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests.test_run_report_endpoint_rejects_unsafe_run_id -v` failed as expected with `404 != 400` for encoded `..` because unsafe run IDs were not rejected before lookup.
- GREEN 3: same targeted test passed after adding safe-run-id validation and JSON `INVALID_RUN_ID` 400 handling.
- API server slice gate: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests -v` passed 5 tests in 3.065s.
- Full suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed 11 tests in 4.630s.
- Compile gate: `python3 -m compileall -q src examples tests` exited 0.
- Manual API smoke: local server on `127.0.0.1:18089` returned health 200/free-beta, `/runs` 200 with `demo-bad,demo-good`, `/runs/demo-good/report` 200 with `mock-good-agent` and 5 attempts, unsafe `%2E%2E` run ID returned 400 `INVALID_RUN_ID`; server was killed after verification.
- Diff whitespace gate: `git diff --check` exited 0.
- README endpoint list updated for `/runs` and `/runs/{runId}/report`.
