# Free beta API preview implementation notes

## Scope

- Launch the next AgentStack Benchmark slice after the HTTP adapter prototype.
- Keep public beta monetization free for now: free public basic runs/leaderboard/report preview; defer paid private/deep reports.
- Add a local API preview foundation without external dependencies so the service can expose health and leaderboard data before a full hosted backend.

## Decisions / assumptions

- Use Python stdlib `http.server` for the first API preview to avoid adding deployment/package complexity in this slice.
- Keep API read-only in this increment: health + leaderboard. Run submission will be a later slice after local run registry/persistence is explicit.
- Expose pricing mode as `free-beta` in API/docs so monetization state is explicit and changeable later.

## Verification log

- RED: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests.test_healthz_declares_free_beta_mode -v` failed as expected with `ModuleNotFoundError: No module named 'agentstack_benchmark.server'` because the API module is not implemented yet.
- GREEN specific: `PYTHONPATH=src python3 -m unittest tests.test_server.APIServerTests -v` passed: 2 tests in 1.249s.
- GREEN suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed: 6 tests in 2.539s.
- Compile gate: `python3 -m compileall -q src examples tests` exited 0 with no stdout.
- Manual API smoke: started `agentstack_benchmark.cli serve` on `127.0.0.1:18088`; `/api/v1/healthz` returned `200 ok free-beta`; `/api/v1/leaderboard` returned `200` with 2 entries and `mock-good-agent` ranked first. Server process was killed after verification.
