# Track field corrective slice

## Scope

GO source: Vladimir accepted Perplexity v2 actualization and explicitly authorized only this local track-slice.

In scope:

- add run-level `track` enum field with allowed values `local-public` and `hosted-verified`;
- default all current local reports/runs to `local-public` only;
- expose `track` in generated report JSON, run registry API responses, leaderboard entries, and local web preview badge;
- keep field as a separate data dimension for future filtering/grouping;
- keep canonical report field order stable by placing `track` immediately after `schemaVersion`.

Out of scope:

- adapter contract;
- hidden tasks;
- auth/rate limits;
- scoring schema changes / scoring_schema_v1 freeze;
- external deploy, public launch, billing/payments/private-key flows.

## Preflight

- `git status --short --branch` → `## main`
- latest commit: `4bda8ab feat: add local web beta preview`
- repo clean before edits.

## RED

- `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_report_declares_local_public_track_with_canonical_order -v`
  - expected failure: report top-level order is currently `['schemaVersion', 'agent', 'taskPack', 'summary']`, missing `track` after `schemaVersion`.

## Implementation decisions

- Added closed run-track enum constants:
  - `local-public`
  - `hosted-verified`
- Local runner assigns only `local-public`.
- `hosted-verified` remains reserved for a future server-side hosted verified runner and is not auto-assigned by local code.
- `track` is stored at run/report level, not as a global service field.
- Generated reports keep canonical top-level order: `schemaVersion`, `track`, `agent`, `taskPack`, `summary`, `attempts`.
- Existing older report artifacts without `track` are canonicalized in read-only registry/leaderboard views as `local-public` without mutating files.
- Leaderboard/run summaries keep `track` as a separate data field for future filtering/grouping, not as display-only text.

## GREEN / verification

- Targeted GREEN:
  - `PYTHONPATH=src python3 -m unittest tests.test_runner.RunnerTests.test_report_declares_local_public_track_with_canonical_order tests.test_runner.RunnerTests.test_run_track_enum_is_closed tests.test_server.APIServerTests.test_leaderboard_endpoint_returns_ranked_runs tests.test_server.APIServerTests.test_run_report_endpoint_returns_one_existing_report tests.test_server.APIServerTests.test_leaderboard_page_renders_ranked_html_preview tests.test_server.APIServerTests.test_run_report_page_renders_existing_report_without_local_paths -v`
  - result: `Ran 6 tests in 2.782s` / `OK`.
- Full suite + compile gate:
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v && python3 -m compileall -q src examples tests`
  - result: `Ran 17 tests in 7.604s` / `OK`; compile gate exit `0`.
- Manual local smoke:
  - generated `/tmp/agentstack-track-smoke-runs/good/report.json` → `track=local-public`, top-level order `['schemaVersion', 'track', 'agent', 'taskPack']`.
  - served local preview on `127.0.0.1:18089` and verified:
    - `runs_status=200`
    - `runs_track=local-public`
    - `leaderboard_track=local-public`
    - `report_wrapper_track=local-public`
    - `report_track=local-public`
    - `html_has_badge=True`
    - `html_has_local_public=True`
  - server process was killed after smoke.
