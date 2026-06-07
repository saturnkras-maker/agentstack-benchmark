# Hosted-verified / hidden-track boundary slice

## Scope

Autonomous v2 mode active. This slice implements the next critical-path item after pilot ×5: hidden/verified track foundation.

In scope:

- expose explicit track capabilities for `local-public` and reserved `hosted-verified`;
- make hidden task policy machine-readable;
- ensure the local runner never assigns `hosted-verified`;
- ensure hidden tasks are rejected by the local-public runner instead of leaking into local/open-source runs;
- expose the capabilities through local API/docs.

Out of scope / GO boundaries:

- no hosted infrastructure;
- no real hidden task corpus;
- no server-side hosted runner;
- no auth/rate limit;
- no public launch;
- no billing;
- no private-key flow or third-party code execution.

## Preflight

- `git status --short --branch && git log --oneline -5`: repo clean on `main`; latest commit `967f77c feat: add local pilot fixtures`.
- Inspected track constants in `schemas.py`, report generation in `runner.py`, run registry/leaderboard propagation, and server API surface.
- Current state already has a closed track enum and local runner default `track: local-public`, but no machine-readable hidden/verified capabilities and no local hidden-task rejection gate.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_tracks.TrackCapabilityTests.test_track_capabilities_define_verified_boundary -v`
  - expected failure: `ModuleNotFoundError: No module named 'agentstack_benchmark.tracks'`.

## GREEN / verification

Implementation:

- added `src/agentstack_benchmark/tracks.py` with explicit track capability metadata;
- added `validate_local_public_task_pack(...)` and wired it into local report generation before agent execution;
- added `GET /api/v1/tracks` on the local API server;
- documented the boundary in `docs/hosted-verified-track-v0.1.md` and README;
- added `tests/test_tracks.py` covering capability shape, API exposure, and rejection of all local hidden markers (`visibility: hidden`, `hidden: true`, `requiresTrack: hosted-verified`) with no `report.json` persisted.

Verification:

- `PYTHONPATH=src python3 -m unittest tests.test_tracks -v`
  - result: `Ran 3 tests in 0.513s` / `OK`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 32 tests in 11.261s` / `OK`; compile gate exit `0`.
- manual API smoke for `GET /api/v1/tracks` with `PYTHONPATH=src`
  - result: `status 200`, `content_type application/json`, `defaultTrack local-public`, `localRunnerCanAssignHostedVerified False`, `hiddenTasksAllowedHostedVerified True`.
- `git diff --check`
  - result: exit `0`.
