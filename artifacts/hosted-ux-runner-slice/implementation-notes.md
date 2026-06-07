# Hosted UX runner slice — implementation notes

## Goal

First repo-local/no-deploy slice of the hosted UX layer: add a browser path where a user can connect a loopback HTTP agent, click Run Benchmark, and get a visual report/leaderboard in the existing local preview server.

## Acceptance criteria

- GET `/run` renders a clear run form and explains the safety boundary.
- POST `/run` accepts agent name/id/version/loopback endpoint/runId, creates a temporary manifest, runs `mvp_v0` via the existing runner, persists `report.json`, and returns links to the visual run report + leaderboard.
- Non-loopback/external endpoints are rejected; no API keys/secrets are accepted or stored in this slice.
- Home UI links to the run form.
- Tests cover form rendering, successful browser-driven run, and rejection path.
- Full unittest + compile pass before report.

## Scope boundaries

- No deploy, no live public hosted runner, no billing, no external endpoint execution.
- No new frontend framework/dependencies; keep stdlib HTML/CSS server style.
- API-key handling remains future work until auth, queueing, secret storage, and abuse controls are designed.

## Implementation summary

- Added `GET /run` browser form to the existing stdlib preview server.
- Added `POST /run` form handling that writes a submitted manifest under the configured `--runs-dir`, invokes the existing `run_benchmark(...)` runner against `examples/task_packs/mvp_v0.json`, and renders a completion page with visual report/leaderboard/JSON links.
- Added loopback-only guard through the existing HTTP adapter validation path; external URLs are rejected before report creation.
- Added human-readable dimension labels in HTML UI while preserving canonical JSON keys.
- Added docs in `docs/hosted-ux-runner-v0.1.md` and README navigation.

## Verification performed

- RED before implementation: `/run` returned `404`, `POST /run` returned `501`, external endpoint rejection did not match the intended UX status.
- Targeted GREEN tests: `3 tests in 2.043s`, `OK` for run form render/success/rejection.
- Full suite after implementation: `Ran 41 tests in 12.540s`, `OK`.
- Compile gate: `python3.11 -m compileall -q src examples tests`, exit `0`.
- Diff hygiene: `git diff --check`, exit `0`.
- Browser proof: submitted `browser-proof-agent` via `/run` to `http://127.0.0.1:8776/tasks`; completion page showed `Overall 98.88`, `5/5`, `local-public`; visual report `/runs/browser-proof-run` showed human-readable dimension labels.

## Deferred next slice

A true external hosted benchmark should add authenticated job submission, async queue/worker isolation, SSRF/egress policy, secure secret storage, public result URLs, and abuse/billing controls before allowing non-loopback endpoints or API keys.
