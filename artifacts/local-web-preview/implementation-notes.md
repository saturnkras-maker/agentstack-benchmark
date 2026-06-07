# Local Web Preview Slice — Implementation Notes

## Scope

Add the next smallest safe local-launch surface for AgentStack Benchmark public beta:

- HTML landing page: `GET /`
- HTML leaderboard: `GET /leaderboard`
- HTML run report: `GET /runs/{runId}`
- Keep existing JSON API endpoints intact.

## Safety boundaries

- No external deploy.
- No live sends.
- No payments, billing, or private-key flows.
- No arbitrary remote execution.
- HTML pages render only existing local `report.json` artifacts and avoid local filesystem path disclosure.
- Web run IDs use the same safe single-segment validation path as the JSON report endpoint.

## Decisions / assumptions

- Used stdlib-only `http.server` rendering to match the existing local API preview and avoid new dependencies.
- Kept the web surface intentionally simple: server-side HTML strings, escaped with `html.escape`, no JavaScript.
- Leaderboard web ranking is derived from existing run summaries and links to `/runs/{runId}`.
- Existing JSON endpoints are preserved; this slice adds HTML routes rather than changing API contracts.

## RED proof

Command:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_server.APIServerTests.test_home_page_renders_public_beta_preview_without_local_paths \
  tests.test_server.APIServerTests.test_leaderboard_page_renders_ranked_html_preview \
  tests.test_server.APIServerTests.test_run_report_page_renders_existing_report_without_local_paths \
  tests.test_server.APIServerTests.test_run_report_page_rejects_unsafe_run_id -v
```

Expected RED result observed before implementation on the four new web behaviors: `/`, `/leaderboard`, and `/runs/good` returned missing HTML behavior, while unsafe `/runs/%2E%2E` returned the wrong status for the new web route.

## GREEN proof

Same targeted command after implementation:

```text
test_home_page_renders_public_beta_preview_without_local_paths ... ok
test_leaderboard_page_renders_ranked_html_preview ... ok
test_run_report_page_renders_existing_report_without_local_paths ... ok
test_run_report_page_rejects_unsafe_run_id ... ok

Ran 4 tests in 2.618s
OK
```

## Implementation cleanup note

During the GREEN pass I hit a local edit collision/duplicate helper artifact while replacing `server.py`. I cleaned it back to a single stdlib implementation and re-ran the targeted tests successfully before moving to broader gates.

## Final verification

- Targeted web tests:

```text
test_home_page_renders_public_beta_preview_without_local_paths ... ok
test_leaderboard_page_renders_ranked_html_preview ... ok
test_run_report_page_renders_existing_report_without_local_paths ... ok
test_run_report_page_rejects_unsafe_run_id ... ok

Ran 4 tests in 2.569s
OK
```

- Full unittest suite:

```text
Ran 15 tests in 7.577s
OK
```

- Compile gate:

```bash
python3 -m compileall -q src examples tests
```

Result: exit code 0, no output.

- Whitespace gate:

```bash
git diff --check
```

Result: exit code 0, no output.

- Manual local smoke via in-process `make_server` against `artifacts/runs`:

```json
{"manual_smoke":"ok","checks":[{"path":"/","status":200,"content_type":"text/html","needle_ok":true},{"path":"/leaderboard","status":200,"content_type":"text/html","needle_ok":true},{"path":"/runs/demo-good","status":200,"content_type":"text/html","needle_ok":true},{"path":"/api/v1/healthz","status":200,"content_type":"application/json","needle_ok":true},{"path":"/runs/%2E%2E","status":400,"content_type":"text/html","needle_ok":true}]}
```
